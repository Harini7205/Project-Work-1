from fastapi import APIRouter, UploadFile, Form, HTTPException
from pathlib import Path
from ipfs.ipfs_helper import upload_to_ipfs
from chameleon_hash.ch_secp256k1 import encode_message, ch_hash, _rand_scalar, forge_r
from blockchain_utils import register_record, redact_record
from zkp.zkp_mock import generate_proof, verify_proof
from key_generation.ecc import generate_ecc_key_pair
from eth_account import Account
from web3 import Web3
import json, os

router = APIRouter(prefix="/ehr", tags=["EHR"])

# ------------------------------
# Directories
# ------------------------------
TEMP_DIR = Path("temp")
TEMP_DIR.mkdir(exist_ok=True)
USER_DB = TEMP_DIR / "users.json"
RECORD_DB = TEMP_DIR / "records.json"

if not USER_DB.exists():
    USER_DB.write_text("{}")
if not RECORD_DB.exists():
    RECORD_DB.write_text("{}")

# ------------------------------
# Blockchain config
# ------------------------------
HARDHAT_RPC = "http://127.0.0.1:7545"
ABI_PATH = Path("./KeyRegistry.json")
CONTRACT_ADDRESS = os.getenv("CONTRACT_ADDRESS")
SENDER_ADDRESS = os.getenv("SENDER_ADDRESS")
SENDER_PRIVATE_KEY = os.getenv("SENDER_PRIVATE_KEY")
w3 = Web3(Web3.HTTPProvider(HARDHAT_RPC))


def load_contract():
    abi = json.loads(open(ABI_PATH).read())
    return w3.eth.contract(address=w3.to_checksum_address(str(CONTRACT_ADDRESS)), abi=abi)

# ------------------------------
# 1️⃣ Register new Patient
# ------------------------------
@router.post("/register")
async def register_patient(name: str = Form(...)):
    """
    Registers a new patient:
    - Generates Ethereum wallet (address + private key)
    - Generates ECC keypair
    - Saves locally and registers ECC public key on blockchain
    """
    users = json.loads(USER_DB.read_text())

    if name in users:
        raise HTTPException(status_code=400, detail="User already exists")

    # Generate Ethereum wallet
    acct = Account.create()
    eth_address = acct.address
    eth_private_key = acct.key.hex()

    # Generate ECC keypair
    sk, pk = generate_ecc_key_pair(save_to_disk=False)
    ecc_private_hex = sk.private_numbers().private_value.to_bytes(32, "big").hex()

    from cryptography.hazmat.primitives import serialization
    ecc_public_bytes = pk.public_bytes(
        encoding=serialization.Encoding.X962,
        format=serialization.PublicFormat.CompressedPoint
    )
    ecc_public_hex = ecc_public_bytes.hex()

    # Store locally
    users[name] = {
        "eth_address": eth_address,
        "eth_private_key": eth_private_key,
        "ecc_private_key": ecc_private_hex,
        "ecc_public_key": ecc_public_hex
    }
    USER_DB.write_text(json.dumps(users, indent=4))

    # Register ECC key on blockchain
    contract = load_contract()
    nonce = w3.eth.get_transaction_count(w3.to_checksum_address(str(SENDER_ADDRESS)))
    try:
        tx = contract.functions.registerKey(ecc_public_bytes).build_transaction({
            "chainId": w3.eth.chain_id,
            "from": str(SENDER_ADDRESS),
            "nonce": nonce,
            "gas": 3000000,
            "gasPrice": w3.to_wei("1", "gwei")
        })
        signed_tx = w3.eth.account.sign_transaction(tx, private_key=SENDER_PRIVATE_KEY)
        tx_hash = w3.eth.send_raw_transaction(signed_tx.raw_transaction)
        w3.eth.wait_for_transaction_receipt(tx_hash)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Blockchain error: {e}")

    return {
        "message": f"Patient '{name}' registered successfully",
        "eth_address": eth_address,
        "tx_hash": tx_hash.hex(),
    }

# ------------------------------
# 2️⃣ Upload and register EHR
# ------------------------------
@router.post("/upload")
async def upload_ehr(file: UploadFile, patient_id: str = Form(...)):
    users = json.loads(USER_DB.read_text())
    records = json.loads(RECORD_DB.read_text())

    if patient_id not in users:
        raise HTTPException(status_code=401, detail="Unauthenticated: Register first")

    # Save uploaded file temporarily
    if not file.filename:
        raise HTTPException(status_code=400, detail="No filename provided.")
    temp_path = TEMP_DIR / file.filename
    with open(temp_path, "wb") as f:
        f.write(await file.read())

    # Upload to IPFS
    cid = upload_to_ipfs(str(temp_path))

    # Compute chameleon hash and r
    identity = bytes.fromhex(users[patient_id]["ecc_public_key"])
    msg = encode_message(cid, True, identity)
    r = _rand_scalar()
    ch_hex, _ = ch_hash(msg, r, identity)

    # Register on blockchain
    tx_hash = register_record(cid, ch_hex, patient_id)

    # Store record locally
    records[patient_id] = {
        "cid": cid,
        "r": hex(r),
        "chameleon_hash": ch_hex
    }
    RECORD_DB.write_text(json.dumps(records, indent=4))

    return {
        "message": "EHR uploaded successfully",
        "cid": cid,
        "tx_hash": tx_hash,
        "chameleon_hash": ch_hex
    }

# ------------------------------
# 3️⃣ Redact EHR
# ------------------------------
@router.post("/redact")
async def redact_ehr(new_file: UploadFile, patient_id: str = Form(...)):
    users = json.loads(USER_DB.read_text())
    records = json.loads(RECORD_DB.read_text())

    if patient_id not in users or patient_id not in records:
        raise HTTPException(status_code=404, detail="Record or user not found")

    # Save new file temporarily
    if not new_file.filename:
        raise HTTPException(status_code=400, detail="No filename provided.")
    new_path = TEMP_DIR / new_file.filename
    with open(new_path, "wb") as f:
        f.write(await new_file.read())

    # Upload new (redacted) version to IPFS
    new_cid = upload_to_ipfs(str(new_path))

    # Load old record data
    old_record = records[patient_id]
    old_cid = old_record["cid"]
    original_r = int(old_record["r"], 16)
    old_ch = old_record["chameleon_hash"]

    # Get identity and private key
    ecc_pub = bytes.fromhex(users[patient_id]["ecc_public_key"])
    ecc_priv = int(users[patient_id]["ecc_private_key"], 16)

    # Compute new r′ using forge_r() → keeps hash constant
    old_msg = encode_message(old_cid, True, ecc_pub)
    new_msg = encode_message(new_cid, True, ecc_pub)
    new_r = forge_r(original_r, ecc_priv, old_msg, new_msg)

    # Update blockchain (same hash, new CID)
    tx_hash = redact_record(patient_id, old_cid, new_cid, old_ch)

    # Update local record
    records[patient_id].update({"cid": new_cid, "r": hex(new_r)})
    RECORD_DB.write_text(json.dumps(records, indent=4))

    return {
        "message": "EHR redacted successfully",
        "new_cid": new_cid,
        "chameleon_hash": old_ch,
        "tx_hash": tx_hash
    }

# ------------------------------
# 4️⃣ Doctor Access Request (ZKP)
# ------------------------------
@router.post("/access-request")
async def request_access(doctor_addr: str = Form(...), patient_id: str = Form(...)):
    users = json.loads(USER_DB.read_text())
    if patient_id not in users:
        raise HTTPException(status_code=401, detail="Patient not registered")

    proof = generate_proof(patient_id)
    verified = verify_proof(proof)
    if not verified:
        return {"error": "Proof verification failed"}

    token = f"TEMP-TOKEN-{doctor_addr[:6]}-{patient_id[:6]}"
    return {"message": "Access granted", "access_token": token}


from fastapi.responses import FileResponse

@router.get("/record/{patient_id}")
async def get_patient_record(patient_id: str):
    """
    Fetches the EHR record for a given patient directly from blockchain,
    downloads from IPFS, and returns the file.
    """
    users = json.loads(USER_DB.read_text())

    if patient_id not in users:
        raise HTTPException(status_code=404, detail="Patient not found")

    # Load smart contract
    contract = load_contract()

    try:
        # 🔗 Fetch record details from blockchain
        _, chameleon_hash, cid, _, _ = contract.functions.getRecord(SENDER_ADDRESS).call()

        if not cid:
            raise HTTPException(status_code=404, detail="No record found for this patient on blockchain")

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Blockchain query failed: {e}")

    # Download the file from IPFS
    downloaded_path = TEMP_DIR / f"{patient_id}_ehr.pdf"
    try:
        from ipfs.ipfs_helper import download_from_ipfs
        download_from_ipfs(cid, str(downloaded_path))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to download from IPFS: {e}")

    # Return file
    headers = {
        "X-Patient-ID": str(patient_id),
        "X-IPFS-CID": str(cid),
        "X-Chameleon-Hash": str(chameleon_hash),
    }

    return FileResponse(
        path=downloaded_path,
        filename=f"{patient_id}_ehr.pdf",
        media_type="application/octet-stream",
        headers=headers
    )
