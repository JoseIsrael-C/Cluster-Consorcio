#!/usr/bin/env python3
"""End-to-end test of verify_certificate.py against a local Hardhat node.

Builds a test PKI (a root CA standing in for the national CA, a timestamp authority, one signing certificate per
campus and a rogue CA), deploys CertificateConsortium with the campus fingerprints, signs PDFs with pyHanko
(PAdES + RFC 3161 timestamp), registers them and checks that the verifier accepts the genuine certificate and
rejects every forgery in the threat model:

  V1 genuine certificate                                   -> accepted
  V2 later incremental update (e.g. LTV data)              -> accepted, same h
  V3 PDF never registered                                  -> check 1 fails
  V4 content altered after signing                         -> checks 1 and 2 fail
  V5 another campus registers a PDF signed by campus 2     -> check 3 fails
  V6 signer certificate from a CA outside the trust anchor -> check 2 fails
  V7 signer certificate revoked (CRL)                      -> check 2 fails
  V8 no RFC 3161 timestamp                                 -> check 2 fails
  V9 certificate revoked on chain                          -> check 1 fails

Run from the kit folder:  python verifier/test_verifier.py   (needs `npx hardhat compile` done once)
"""
import datetime as dt
import hashlib
import io
import json
import os
import socket
import subprocess
import sys
import tempfile
import time

from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.x509.oid import NameOID, ExtendedKeyUsageOID
from asn1crypto import x509 as asn1_x509, keys as asn1_keys
from pyhanko.pdf_utils import generic
from pyhanko.pdf_utils.incremental_writer import IncrementalPdfFileWriter
from pyhanko.pdf_utils.writer import PdfFileWriter
from pyhanko.pdf_utils.content import RawContent
from pyhanko.pdf_utils.layout import BoxConstraints
from pyhanko.sign import signers
from pyhanko.sign.fields import SigSeedSubFilter
from pyhanko.sign.timestamps.dummy_client import DummyTimeStamper
from pyhanko_certvalidator.registry import SimpleCertificateStore
from web3 import Web3

HERE = os.path.dirname(os.path.abspath(__file__))
KIT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
import verify_certificate as V  # noqa: E402
import logging  # noqa: E402
logging.getLogger("pyhanko").setLevel(logging.CRITICAL)
logging.getLogger("pyhanko_certvalidator").setLevel(logging.CRITICAL)

PORT = int(os.environ.get("VERIFIER_TEST_PORT", "8547"))
GW_PORT = PORT + 54
RPC = f"http://127.0.0.1:{PORT}"
GW = f"http://127.0.0.1:{GW_PORT}"
NOW = dt.datetime.now(dt.timezone.utc)
CDP = "http://crl.example.invalid/ac.crl"


# ------------------------------------------------------------------ test PKI
def name(cn):
    return x509.Name([x509.NameAttribute(NameOID.COUNTRY_NAME, "MX"),
                      x509.NameAttribute(NameOID.ORGANIZATION_NAME, "Test PKI"),
                      x509.NameAttribute(NameOID.COMMON_NAME, cn)])


def new_key():
    return rsa.generate_private_key(public_exponent=65537, key_size=2048)


def make_cert(cn, key, issuer_name, issuer_key, ca=False, eku=None):
    b = (x509.CertificateBuilder().subject_name(name(cn)).issuer_name(issuer_name)
         .public_key(key.public_key()).serial_number(x509.random_serial_number())
         .not_valid_before(NOW - dt.timedelta(days=1)).not_valid_after(NOW + dt.timedelta(days=365))
         .add_extension(x509.BasicConstraints(ca=ca, path_length=None), critical=True)
         .add_extension(x509.SubjectKeyIdentifier.from_public_key(key.public_key()), critical=False)
         .add_extension(x509.AuthorityKeyIdentifier.from_issuer_public_key(issuer_key.public_key()), critical=False))
    if ca:
        b = b.add_extension(x509.KeyUsage(False, False, False, False, False, True, True, False, False), critical=True)
    else:
        b = b.add_extension(x509.KeyUsage(True, True, False, False, False, False, False, False, False), critical=True)
        b = b.add_extension(x509.CRLDistributionPoints([x509.DistributionPoint(
            [x509.UniformResourceIdentifier(CDP)], None, None, None)]), critical=False)
    if eku:
        b = b.add_extension(x509.ExtendedKeyUsage(eku), critical=True)
    return b.sign(issuer_key, hashes.SHA256())


def make_crl(ca_cert, ca_key, revoked=()):
    b = (x509.CertificateRevocationListBuilder().issuer_name(ca_cert.subject)
         .last_update(NOW - dt.timedelta(hours=1)).next_update(NOW + dt.timedelta(days=7))
         .add_extension(x509.AuthorityKeyIdentifier.from_issuer_public_key(ca_key.public_key()), critical=False)
         .add_extension(x509.CRLNumber(1), critical=False))
    for c in revoked:
        b = b.add_revoked_certificate(x509.RevokedCertificateBuilder().serial_number(c.serial_number)
                                      .revocation_date(NOW - dt.timedelta(minutes=30)).build())
    return b.sign(ca_key, hashes.SHA256()).public_bytes(serialization.Encoding.DER)


def asn1_cert(c):
    return asn1_x509.Certificate.load(c.public_bytes(serialization.Encoding.DER))


def asn1_key(k):
    return asn1_keys.PrivateKeyInfo.load(k.private_bytes(serialization.Encoding.DER,
                                                         serialization.PrivateFormat.PKCS8,
                                                         serialization.NoEncryption()))


class PKI:
    def __init__(self):
        self.ca_key = new_key()
        self.ca = make_cert("Root CA (stands in for the national CA)", self.ca_key, name("Root CA (stands in for the national CA)"), self.ca_key, ca=True)
        self.tsa_key = new_key()
        self.tsa = make_cert("Test TSA", self.tsa_key, self.ca.subject, self.ca_key, eku=[ExtendedKeyUsageOID.TIME_STAMPING])
        self.campus_keys = [new_key() for _ in range(6)]  # index 0 unused: campus ids are 1..5
        self.campus = [make_cert(f"Campus {i} signing certificate", k, self.ca.subject, self.ca_key)
                       for i, k in enumerate(self.campus_keys)]
        self.rogue_ca_key = new_key()
        self.rogue_ca = make_cert("Rogue CA", self.rogue_ca_key, name("Rogue CA"), self.rogue_ca_key, ca=True)
        self.rogue_key = new_key()
        self.rogue = make_cert("Campus 2 signing certificate", self.rogue_key, self.rogue_ca.subject, self.rogue_ca_key)

    def fingerprint(self, c):
        return hashlib.sha256(c.public_bytes(serialization.Encoding.DER)).digest()

    def timestamper(self):
        return DummyTimeStamper(tsa_cert=asn1_cert(self.tsa), tsa_key=asn1_key(self.tsa_key),
                                certs_to_embed=SimpleCertificateStore.from_certs([asn1_cert(self.ca)]))

    def signer(self, cert, key, ca):
        return signers.SimpleSigner(signing_cert=asn1_cert(cert), signing_key=asn1_key(key),
                                    cert_registry=SimpleCertificateStore.from_certs([asn1_cert(ca)]))


# ------------------------------------------------------------------ PDFs
def blank_pdf(text):
    w = PdfFileWriter()
    stream = f"BT /F1 14 Tf 72 720 Td ({text}) Tj ET".encode()
    font = generic.DictionaryObject({generic.NameObject("/Type"): generic.NameObject("/Font"),
                                     generic.NameObject("/Subtype"): generic.NameObject("/Type1"),
                                     generic.NameObject("/BaseFont"): generic.NameObject("/Helvetica")})
    res = generic.DictionaryObject({generic.NameObject("/Font"): generic.DictionaryObject(
        {generic.NameObject("/F1"): w.add_object(font)})})
    page = generic.DictionaryObject({
        generic.NameObject("/Type"): generic.NameObject("/Page"),
        generic.NameObject("/MediaBox"): generic.ArrayObject([generic.NumberObject(x) for x in (0, 0, 612, 792)]),
        generic.NameObject("/Resources"): res,
        generic.NameObject("/Contents"): w.add_object(generic.StreamObject(stream_data=stream)),
    })
    w.insert_page(page)
    out = io.BytesIO()
    w.write(out)
    return out.getvalue()


def sign(pdf, signer, timestamper=None):
    meta = signers.PdfSignatureMetadata(field_name="Issuance", subfilter=SigSeedSubFilter.PADES)
    out = signers.sign_pdf(IncrementalPdfFileWriter(io.BytesIO(pdf)), meta, signer=signer, timestamper=timestamper)
    return out.getvalue()


def add_incremental_update(pdf):
    """Append an innocuous incremental update (as LTV tools do): new Info dictionary entry."""
    w = IncrementalPdfFileWriter(io.BytesIO(pdf))
    w.set_info(generic.DictionaryObject({generic.NameObject("/Producer"): generic.TextStringObject("LTV update")}))
    out = io.BytesIO()
    w.write(out)
    return out.getvalue()


def doc_hash(pdf):
    _, s = V.first_signature(pdf)
    return V.document_hash(pdf, s)


# ------------------------------------------------------------------ chain
def wait_port(port, timeout=60):
    t0 = time.time()
    while time.time() - t0 < timeout:
        try:
            socket.create_connection(("127.0.0.1", port), 1).close()
            return
        except OSError:
            time.sleep(0.5)
    raise RuntimeError("hardhat node did not start")


def deploy(w3, fingerprints):
    art = json.load(open(os.path.join(KIT, "artifacts/contracts/CertificateConsortium.sol/CertificateConsortium.json")))
    accts = w3.eth.accounts[:5]
    C = w3.eth.contract(abi=art["abi"], bytecode=art["bytecode"])
    tx = C.constructor(accts, [1, 2, 3, 4, 5], fingerprints).transact({"from": accts[0]})
    addr = w3.eth.wait_for_transaction_receipt(tx).contractAddress
    return w3.eth.contract(address=addr, abi=art["abi"]), accts


def issue(c, frm, h):
    w3 = c.w3
    w3.eth.wait_for_transaction_receipt(c.functions.issue(h, 1).transact({"from": frm}))


# ------------------------------------------------------------------ main
def main():
    tmp = tempfile.mkdtemp(prefix="verifier-")
    log = open(os.path.join(tmp, "hardhat-node.log"), "w")
    node = subprocess.Popen(["npx", "hardhat", "node", "--port", str(PORT)], cwd=KIT, stdout=log, stderr=log)
    results = []
    procs = []
    try:
        wait_port(PORT)
        w3 = Web3(Web3.HTTPProvider(RPC))
        pki = PKI()
        c, accts = deploy(w3, [pki.fingerprint(x) for x in pki.campus[1:]])
        logdir = os.path.join(tmp, "gateway-logs")
        os.makedirs(logdir)
        open(os.path.join(logdir, "gateway-2020-01-01.log"), "w").write("{}\n")  # older than the retention period
        gw = subprocess.Popen(["node", "scripts/readonly-gateway.js"], cwd=KIT, stdout=log, stderr=log, env={
            **os.environ, "UPSTREAM": RPC, "CONTRACT": c.address, "PORT": str(GW_PORT), "LOG_DIR": logdir, "RETENTION_DAYS": "90"})
        procs.append(gw)
        wait_port(GW_PORT)
        acct = lambda campus: accts[campus - 1]
        anchors = [asn1_cert(pki.ca)]
        crl_ok = [make_crl(pki.ca, pki.ca_key)]
        crl_rev = [make_crl(pki.ca, pki.ca_key, revoked=[pki.campus[2]])]
        ts = pki.timestamper()
        s2 = pki.signer(pki.campus[2], pki.campus_keys[2], pki.ca)

        def run(label, pdf, expect_ok, expect_fail=(), crls=crl_ok):
            path = os.path.join(tmp, label + ".pdf")
            open(path, "wb").write(pdf)
            r = V.verify(path, GW, c.address, anchors, None, crls, fetch=False, soft_fail=False)
            failed = sorted(k for k, v in r["checks"].items() if not v["ok"])
            ok = r["accepted"] == expect_ok and all(f in failed for f in expect_fail)
            if expect_ok:
                ok = ok and not failed
            results.append((label, ok, failed, r))
            mark = "ok  " if ok else "FAIL"
            print(f"  {mark} {label:<58} accepted={r['accepted']!s:<5} failed={failed}")

        # V1 genuine
        genuine = sign(blank_pdf("Titulo profesional 0001"), s2, ts)
        issue(c, acct(2), doc_hash(genuine))
        run("V1 genuine certificate", genuine, True)
        # V2 later incremental update keeps h
        updated = add_incremental_update(genuine)
        assert doc_hash(updated) == doc_hash(genuine)
        run("V2 incremental update after signing (same h)", updated, True)
        # V3 never registered
        run("V3 signed but never registered", sign(blank_pdf("Titulo profesional 0002"), s2, ts), False, ["registry"])
        # V4 altered content: flip one byte inside the signed range (the page text)
        bad = bytearray(genuine)
        i = bad.find(b"Titulo profesional 0001")
        bad[i + 22:i + 23] = b"9"
        run("V4 content altered after signing", bytes(bad), False, ["registry", "signature"])
        # V5 another campus registers a PDF signed by campus 2
        other = sign(blank_pdf("Titulo profesional 0003"), s2, ts)
        issue(c, acct(3), doc_hash(other))
        run("V5 registered by campus 3, signed by campus 2", other, False, ["binding"])
        # V6 rogue CA certificate with the same subject as campus 2, registered by campus 2
        rogue = sign(blank_pdf("Titulo profesional 0004"), pki.signer(pki.rogue, pki.rogue_key, pki.rogue_ca), ts)
        issue(c, acct(2), doc_hash(rogue))
        run("V6 signer outside the trust anchor (rogue CA)", rogue, False, ["signature", "binding"])
        # V7 revoked signer certificate
        run("V7 signer certificate revoked in the CA's CRL", genuine, False, ["signature"], crls=crl_rev)
        # V8 no timestamp
        nots = sign(blank_pdf("Titulo profesional 0005"), s2, None)
        issue(c, acct(2), doc_hash(nots))
        run("V8 no RFC 3161 timestamp", nots, False, ["signature"])
        # V9 revoked on chain by the issuing campus
        rev = sign(blank_pdf("Titulo profesional 0006"), s2, ts)
        issue(c, acct(2), doc_hash(rev))
        cid = c.functions.idByHash(doc_hash(rev)).call()
        w3.eth.wait_for_transaction_receipt(c.functions.revoke(cid).transact({"from": acct(2)}))
        run("V9 certificate revoked on chain", rev, False, ["registry"])

        # gateway properties
        import urllib.request
        def rpc(payload):
            req = urllib.request.Request(GW, json.dumps(payload).encode(), {"content-type": "application/json"})
            return json.loads(urllib.request.urlopen(req).read())
        tx = {"from": acct(1), "to": c.address, "data": c.functions.issue(b"\x01" * 32, 1)._encode_transaction_data()}
        refused = [
            rpc({"jsonrpc": "2.0", "id": 1, "method": "eth_sendTransaction", "params": [tx]}),
            rpc({"jsonrpc": "2.0", "id": 2, "method": "eth_call", "params": [{"to": c.address, "data": tx["data"]}, "latest"]}),
            rpc({"jsonrpc": "2.0", "id": 3, "method": "eth_getLogs", "params": [{}]}),
            rpc({"jsonrpc": "2.0", "id": 4, "method": "eth_call", "params": [{"to": acct(1), "data": "0x75e36616" + "00" * 32}, "latest"]}),
        ]
        g1 = all("error" in r for r in refused)
        results.append(("G1 writes and other calls refused by the gateway", g1, [], {"accepted": None}))
        print(f"  {'ok  ' if g1 else 'FAIL'} G1 writes and other calls refused by the gateway")
        logtext = "".join(open(os.path.join(logdir, f)).read() for f in os.listdir(logdir))
        hashes = [doc_hash(genuine).hex(), doc_hash(other).hex(), doc_hash(rogue).hex()]
        g2 = (logtext.count("eth_call:verify") >= 9 and not any(h.removeprefix("0x") in logtext for h in hashes)
              and "127.0.0.0/24" in logtext and "127.0.0.1\"" not in logtext)
        results.append(("G2 gateway log holds no hash and a truncated address", g2, [], {"accepted": None}))
        print(f"  {'ok  ' if g2 else 'FAIL'} G2 gateway log holds no hash and a truncated address")
        g3 = not os.path.exists(os.path.join(logdir, "gateway-2020-01-01.log"))
        results.append(("G3 logs older than the retention period deleted", g3, [], {"accepted": None}))
        print(f"  {'ok  ' if g3 else 'FAIL'} G3 logs older than the retention period deleted")
    finally:
        for p in procs:
            p.terminate()
        node.terminate()
        node.wait(timeout=10)
    passed = sum(1 for r in results if r[1])
    print(f"\n{passed}/{len(results)} verifier cases behave as expected")
    out = os.path.join(KIT, "results", "verifier-test.json")
    os.makedirs(os.path.dirname(out), exist_ok=True)
    json.dump([{"case": l, "asExpected": ok, "failedChecks": f, "accepted": r["accepted"]} for l, ok, f, r in results],
              open(out, "w"), indent=2)
    sys.exit(0 if passed == len(results) else 1)


if __name__ == "__main__":
    main()
