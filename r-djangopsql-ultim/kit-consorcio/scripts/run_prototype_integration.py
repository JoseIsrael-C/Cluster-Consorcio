"""Runs the prototype's own blockchain integration (management/contrato.py, unmodified) against a local
node and records the gas of every call. The prototype hard-codes Ganache at 127.0.0.1:7545, a contract
address and a private key, so this harness (1) deploys CertificadosContract.sol, (2) places its runtime
code and admin slot at the hard-coded address, (3) funds the hard-coded account, and then (4) imports
contrato.py as is and calls its functions with records built like the prototype's views.

    npx hardhat node --port 7545 &
    python scripts/run_prototype_integration.py <path to the prototype's management/ folder>
"""
import importlib, json, os, subprocess, sys, statistics, traceback
from web3 import Web3

PROTO = sys.argv[1]
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RUNS = 30
w3 = Web3(Web3.HTTPProvider("http://127.0.0.1:7545"))
assert w3.is_connected(), "start: npx hardhat node --port 7545"

art = json.load(open(os.path.join(ROOT, "artifacts/contracts/prototype/CertificadosContract.sol/CertificadosContract.json")))
src = open(os.path.join(PROTO, "contrato.py"), encoding="utf8").read()
HARD_ADDR = Web3.to_checksum_address(src.split("direccion_contrato = '")[1].split("'")[0])
KEY = src.split('from_key("')[1].split('"')[0]
acct = w3.eth.account.from_key(KEY)

# Fund the prototype's account, deploy, and move the contract to the hard-coded address.
w3.provider.make_request("hardhat_setBalance", [acct.address, hex(10**21)])
Factory = w3.eth.contract(abi=art["abi"], bytecode=art["bytecode"])
tx = Factory.constructor().build_transaction({"from": acct.address, "nonce": w3.eth.get_transaction_count(acct.address), "gasPrice": w3.to_wei(2, "gwei")})
rc = w3.eth.wait_for_transaction_receipt(w3.eth.send_raw_transaction(acct.sign_transaction(tx).raw_transaction))
deploy_gas = rc.gasUsed
runtime = w3.eth.get_code(rc.contractAddress)
w3.provider.make_request("hardhat_setCode", [HARD_ADDR, "0x" + runtime.hex().removeprefix("0x")])
w3.provider.make_request("hardhat_setStorageAt", [HARD_ADDR, "0x0", "0x" + acct.address[2:].lower().rjust(64, "0")])

# Import the prototype's integration module unchanged.
sys.path.insert(0, PROTO)
contrato = importlib.import_module("contrato")

data = json.loads(subprocess.check_output(["node", "-e",
    "const {record}=require('./scripts/prototype-data');console.log(JSON.stringify([...Array(%d).keys()].map(i=>record(i))))" % RUNS], cwd=ROOT))

def gas_of(h):
    return w3.eth.get_transaction_receipt(h).gasUsed

out = {"web3": importlib.import_module("web3").__version__, "deploymentGas": deploy_gas, "calls": {}, "errors": {}}
def run(name, fn):
    try:
        out["calls"][name] = fn()
    except Exception as e:  # record the failure exactly as the prototype would hit it
        out["errors"][name] = f"{type(e).__name__}: {e}"[:300]

def issue_A():
    gas, failed = [], []
    for i, r in enumerate(data):
        try:
            rec = contrato.emitir_certificado(*r["A"])
            gas.append(gas_of(rec["hash"]))
        except Exception as e:
            failed.append({"record": i, "bytes": len("".join(r["A"][1:]).encode()), "error": f"{type(e).__name__}"})
    return {"n": len(gas), "mean": statistics.mean(gas), "sd": statistics.stdev(gas), "failed": len(failed),
            "failedRecords": failed}

def issue_B():
    gas = []
    for r in data:
        rec = contrato.emitir_certificado(*r["B"])
        gas.append(gas_of(rec["hash"]))
    return {"n": len(gas), "mean": statistics.mean(gas), "sd": statistics.stdev(gas)}

run("emitir_certificado_patternA", issue_A)
run("emitir_certificado_patternB", issue_B)
run("validar_certificado", lambda: [contrato.validar_certificado(r["B"][0]) for r in data[:5]])
run("obtener_certificado", lambda: list(contrato.obtener_certificado(data[0]["B"][0])))
run("revocar_certificado", lambda: gas_of(contrato.revocar_certificado(data[1]["B"][0]).transactionHash))
run("emitir_hash_alumno", lambda: gas_of(contrato.emitir_hash_alumno(4242, "LOHM040512MMCPRR05", "236022004",
    "María Fernanda López Hernández", "Ingeniería en Sistemas Computacionales", "2004-05-12")["hash"]))

os.makedirs(os.path.join(ROOT, "results"), exist_ok=True)
json.dump(out, open(os.path.join(ROOT, "results/prototype-integration.json"), "w"), indent=2, ensure_ascii=False)
print(json.dumps(out, indent=2, ensure_ascii=False))
