from web3 import Web3
import json

# Conexión a Ganache local (por defecto: puerto 7545)
ganache_url = "http://127.0.0.1:7545"
web3 = Web3(Web3.HTTPProvider(ganache_url))

chain_id = 1337
# Verifica conexión
if not web3.is_connected():
    raise Exception("No se pudo conectar a Ganache")

# Dirección del contrato desplegado correctamente en Ganache
direccion_contrato = '0x01B92f099dA2868174f8e1718e06a555625f2b24'

# ABI del contrato (copiado desde Remix)
abi = [
	{
		"inputs": [],
		"stateMutability": "nonpayable",
		"type": "constructor"
	},
	{
		"inputs": [],
		"name": "admin",
		"outputs": [
			{
				"internalType": "address",
				"name": "",
				"type": "address"
			}
		],
		"stateMutability": "view",
		"type": "function"
	},
	{
		"inputs": [
			{
				"internalType": "uint256",
				"name": "",
				"type": "uint256"
			}
		],
		"name": "certificados",
		"outputs": [
			{
				"internalType": "uint256",
				"name": "id",
				"type": "uint256"
			},
			{
				"internalType": "string",
				"name": "nombre",
				"type": "string"
			},
			{
				"internalType": "string",
				"name": "apellidoPaterno",
				"type": "string"
			},
			{
				"internalType": "string",
				"name": "apellidoMaterno",
				"type": "string"
			},
			{
				"internalType": "string",
				"name": "matricula",
				"type": "string"
			},
			{
				"internalType": "string",
				"name": "curso",
				"type": "string"
			},
			{
				"internalType": "string",
				"name": "fechaEmision",
				"type": "string"
			},
			{
				"internalType": "bool",
				"name": "esValido",
				"type": "bool"
			}
		],
		"stateMutability": "view",
		"type": "function"
	},
	{
		"inputs": [
			{
				"internalType": "uint256",
				"name": "_id",
				"type": "uint256"
			},
			{
				"internalType": "string",
				"name": "_nombre",
				"type": "string"
			},
			{
				"internalType": "string",
				"name": "_apellidoPaterno",
				"type": "string"
			},
			{
				"internalType": "string",
				"name": "_apellidoMaterno",
				"type": "string"
			},
			{
				"internalType": "string",
				"name": "_matricula",
				"type": "string"
			},
			{
				"internalType": "string",
				"name": "_curso",
				"type": "string"
			},
			{
				"internalType": "string",
				"name": "_fechaEmision",
				"type": "string"
			}
		],
		"name": "emitirCertificado",
		"outputs": [],
		"stateMutability": "nonpayable",
		"type": "function"
	},
	{
		"inputs": [
			{
				"internalType": "uint256",
				"name": "_id",
				"type": "uint256"
			}
		],
		"name": "obtenerCertificado",
		"outputs": [
			{
				"internalType": "string",
				"name": "nombre",
				"type": "string"
			},
			{
				"internalType": "string",
				"name": "apellidoPaterno",
				"type": "string"
			},
			{
				"internalType": "string",
				"name": "apellidoMaterno",
				"type": "string"
			},
			{
				"internalType": "string",
				"name": "matricula",
				"type": "string"
			},
			{
				"internalType": "string",
				"name": "curso",
				"type": "string"
			},
			{
				"internalType": "string",
				"name": "fechaEmision",
				"type": "string"
			},
			{
				"internalType": "bool",
				"name": "esValido",
				"type": "bool"
			}
		],
		"stateMutability": "view",
		"type": "function"
	},
	{
		"inputs": [
			{
				"internalType": "uint256",
				"name": "_id",
				"type": "uint256"
			}
		],
		"name": "revocarCertificado",
		"outputs": [],
		"stateMutability": "nonpayable",
		"type": "function"
	},
	{
		"inputs": [
			{
				"internalType": "address",
				"name": "nuevoAdmin",
				"type": "address"
			}
		],
		"name": "transferirAdmin",
		"outputs": [],
		"stateMutability": "nonpayable",
		"type": "function"
	},
	{
		"inputs": [
			{
				"internalType": "uint256",
				"name": "_id",
				"type": "uint256"
			}
		],
		"name": "validarCertificado",
		"outputs": [
			{
				"internalType": "bool",
				"name": "",
				"type": "bool"
			}
		],
		"stateMutability": "view",
		"type": "function"
	}
]

# Instancia del contrato
contrato = web3.eth.contract(address=direccion_contrato, abi=abi)

# Usar la primera cuenta de Ganache (siempre tiene fondos)
# Puedes cambiar esta clave por la primera cuenta que aparece en tu Ganache
try:
    # Intentar usar la primera cuenta disponible en Ganache
    cuentas = web3.eth.accounts
    if cuentas:
        cuenta_address = cuentas[0]
        # Clave privada de tu Ganache
        cuenta = web3.eth.account.from_key("0xeac7161f44d902de70e7a617654729340541beddabf6446a891d812dc3fa3e96")
    else:
        # Fallback a tu cuenta de Ganache
        cuenta = web3.eth.account.from_key("0xac6675c80db95bf12d1e42f489dcfd1de2f467f284e66e5cd3b0e848c929a132")
except:
    # Si hay error, usar tu cuenta de Ganache
    cuenta = web3.eth.account.from_key("0xac6675c80db95bf12d1e42f489dcfd1de2f467f284e66e5cd3b0e848c929a132")

#desde aqui empieza el otro contrato.
def emitir_certificado(id, nombre, ap_paterno, ap_materno, matricula, curso, fecha):
    nonce = web3.eth.get_transaction_count(cuenta.address)
    tx = contrato.functions.emitirCertificado(
        id, nombre, ap_paterno, ap_materno, matricula, curso, fecha
    ).build_transaction({
        'from': cuenta.address,
        'nonce': nonce,
        'gas': 300000,  # Reducido para evitar costos altos
        'gasPrice': web3.to_wei('2', 'gwei')  # Precio consistente
    })
    signed_tx = web3.eth.account.sign_transaction(tx, private_key=cuenta.key)
    tx_hash = web3.eth.send_raw_transaction(signed_tx.raw_transaction)
    receipt1 = web3.eth.wait_for_transaction_receipt(tx_hash)
    receipt = {
        "hash": web3.to_hex(tx_hash),
        "hash2": receipt1["blockHash"],
        "blocke": receipt1['blockNumber'],
        "transBlock": receipt1['transactionHash'],
        "nonce": nonce,
        "nonce2": receipt1["status"]
	}
    return receipt

## esta funcion no la voy a necesitar. al parecer o no se para que sea 
def obtener_certificado(id):
    print(id)
    result = contrato.functions.obtenerCertificado(id).call()
    print(result)
    return result

#funcion para validad certificado
def validar_certificado(id):
    #print(contrato.functions.validarCertificado(2).call())
    return contrato.functions.validarCertificado(id).call()

#funcion para revocar certificado
def revocar_certificado(id):
    nonce = web3.eth.get_transaction_count(cuenta.address)

	#contruccion de la transaccion
    # Construcción de la transacción
    transaccion = contrato.functions.revocarCertificado(id).build_transaction({
        'from': cuenta.address,
        'nonce': nonce,
        'gas': 200000,
        'gasPrice': web3.to_wei('2', 'gwei')  # Precio consistente
        #'chainId': chain_id
    })

    # Firmar y enviar
    transaccion_firmada = web3.eth.account.sign_transaction(transaccion, private_key=cuenta.key)
    tx_hash = web3.eth.send_raw_transaction(transaccion_firmada.rawTransaction)
    receipt = web3.eth.wait_for_transaction_receipt(tx_hash)
    #receipt = web3.to_hex(tx_hash)
    return receipt

def verificar_transaccion(tx_hash):
    """
    Verifica una transacción en la blockchain usando su hash.
    Retorna el recibo de la transacción si existe, o None si no.
    """
    try:
        receipt = web3.eth.get_transaction_receipt(tx_hash)
        return receipt
    except Exception:
        return None

def emitir_hash_alumno(alumno_id, curp, matricula, nombre_completo, carrera, fecha_nacimiento):
    """
    Emite un hash único del alumno en la blockchain con datos personales únicos.
    """
    import hashlib
    from datetime import datetime
    
    # Crear un hash único con datos del alumno
    datos_alumno = f"{alumno_id}_{curp}_{matricula}_{nombre_completo}_{carrera}_{fecha_nacimiento}_{datetime.now().isoformat()}"
    hash_datos = hashlib.sha256(datos_alumno.encode()).hexdigest()
    
    # Emitir certificado con el hash único
    nonce = web3.eth.get_transaction_count(cuenta.address)
    tx = contrato.functions.emitirCertificado(
        alumno_id,  # ID único del alumno
        nombre_completo,  # Nombre completo
        curp,  # CURP como apellido paterno
        matricula,  # Matrícula como apellido materno
        carrera,  # Carrera como matrícula
        f"Hash Alumno: {hash_datos[:20]}",  # Curso con hash
        datetime.now().strftime("%d/%m/%Y")  # Fecha actual
    ).build_transaction({
        'from': cuenta.address,
        'nonce': nonce,
        'gas': 300000,
        'gasPrice': web3.to_wei('2', 'gwei')
    })
    
    signed_tx = web3.eth.account.sign_transaction(tx, private_key=cuenta.key)
    tx_hash = web3.eth.send_raw_transaction(signed_tx.raw_transaction)
    receipt1 = web3.eth.wait_for_transaction_receipt(tx_hash)
    
    receipt = {
        "hash": web3.to_hex(tx_hash),
        "hash2": receipt1["blockHash"],
        "blocke": receipt1['blockNumber'],
        "transBlock": receipt1['transactionHash'],
        "nonce": nonce,
        "nonce2": receipt1["status"],
        "hash_alumno": hash_datos  # Hash único del alumno
    }
    return receipt
