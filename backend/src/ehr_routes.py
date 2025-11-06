from fastapi import APIRouter, UploadFile, Form, HTTPException
from ipfs.ipfs_helper import (
    upload_to_ipfs_bytes as upload_to_ipfs,
    download_from_ipfs_bytes as download_from_ipfs
)
from ipfs.aes_gcm import encrypt_bytes
from chameleon_hash.ch_secp256k1 import encode_message, ch_hash, _rand_scalar, forge_r
from zkp.zkp_mock import generate_proof
from key_generation.ecc import generate_ecc_key_pair
from fastapi.responses import StreamingResponse
from web3 import Web3
import json, io
import time

# blockchain helpers return tx_data
from blockchain_utils import (
    register_identity,
    store_record,
    update_record,
    submit_access_request
)

router = APIRouter(prefix="/ehr", tags=["EHR"])


###############################################################
# ✅ 1) USER KEYPAIR GENERATION
###############################################################
@router.post("/generate-keys")
async def generate_keys():
    sk, pk = generate_ecc_key_pair(save_to_disk=False)

    from cryptography.hazmat.primitives import serialization
    ecc_public_bytes = pk.public_bytes(
        encoding=serialization.Encoding.X962,
        format=serialization.PublicFormat.CompressedPoint
    )
    ecc_public_hex = ecc_public_bytes.hex()
    ecc_private_hex = sk.private_numbers().private_value.to_bytes(32, "big").hex()

    return {
        "private_key": ecc_private_hex,
        "public_key": ecc_public_hex
    }


###############################################################
# ✅ 2) REGISTER IDENTITY — return tx
###############################################################
@router.post("/register")
async def register_identity_api(
    public_key_hex: str = Form(...),
    eth_address: str = Form(...),
    name: str = Form(...)
):
    pk_bytes = bytes.fromhex(public_key_hex)

    tx_data = register_identity(
        eth_address=eth_address,
        pubkey_bytes=pk_bytes, 
        name=name
    )

    return {
        "message": "Identity prepared — sign via MetaMask",
        "tx_data": tx_data
    }


###############################################################
# ✅ 3) UPLOAD EHR → CH + ZKP → tx_data
###############################################################

###############################################################
# ✅ (1) Encrypt EHR  — mock
###############################################################
@router.post("/encrypt")
async def encrypt_ehr(file: UploadFile):
    """
    Step-1: User uploads raw EHR
    → returns encrypted bytes
    (Here, just mock encryption)
    """
    raw = await file.read()

    encrypted = encrypt_bytes(raw)

    return StreamingResponse(
    io.BytesIO(encrypted),
    media_type="application/octet-stream"
)



###############################################################
# ✅ (2) Upload encrypted file → IPFS
###############################################################
@router.post("/ipfs-upload")
async def upload_ipfs(file: UploadFile):
    enc_bytes = await file.read()

    cid = upload_to_ipfs(enc_bytes)

    return {
        "message": "Uploaded to IPFS",
        "cid": cid,
    }


###############################################################
# ✅ (3) Compute Chameleon Hash
###############################################################
@router.post("/chameleon-hash/{cid}")
async def compute_ch(cid: str, public_key_hex: str = Form(...)):
    """
    Uses cid only → returns chameleon hash + random r
    """
    # For demo — no real consent/public key used
    msg = encode_message(cid, True, bytes.fromhex(public_key_hex))

    r = _rand_scalar()
    ch_hex, _ = ch_hash(msg, r, bytes.fromhex(public_key_hex))

    return {
        "message": "Chameleon hash computed",
        "ch": ch_hex,
        "r": hex(r)
    }


###############################################################
# ✅ (4) Store on chain
###############################################################
@router.post("/store-record")
async def store_record_endpoint(
    cid: str = Form(...),
    ch: str = Form(...),
    eth_address: str = Form(...)
):
    """
    Step-4: Produce unsigned tx → MetaMask
    """
    # recordId = keccak(cid + wallet)
    record_id = Web3.keccak(text=cid + eth_address).hex()

    tx_data = store_record(
        eth_address=eth_address,
        record_id=record_id,
        ch_hash=ch,
        cid=cid,
        consent=True
    )

    return {
        "message": "TX ready — sign via MetaMask",
        "record_id": record_id,
        "tx_data": tx_data
    }


###############################################################
# ✅ 4) REDACTION → tx_data
###############################################################
@router.post("/redact")
async def redact_ehr(
    file: UploadFile,
    old_cid: str = Form(...),
    public_key_hex: str = Form(...),
    private_key_hex: str = Form(...),
    c_hash: str = Form(...),
    old_r_hex: str = Form(...),
    record_id: str = Form(...),
    eth_address: str = Form(...),
    consent_active: bool = Form(...)
):
    # Read new encrypted bytes
    new_bytes = await file.read()
    new_cid = upload_to_ipfs(new_bytes)

    # Compute new r'
    pub = bytes.fromhex(public_key_hex)
    sk = int(private_key_hex, 16)
    old_r = int(old_r_hex, 16)

    old_msg = encode_message(old_cid, consent_active, pub)
    new_msg = encode_message(new_cid, consent_active, pub)

    new_r = forge_r(old_r, sk, old_msg, new_msg)

    # Build tx — FE signs
    tx_data = update_record(
        eth_address=eth_address,
        record_id=record_id,
        cid=new_cid,
        ch_hash=c_hash
    )

    new_ch_hash, _ = ch_hash(new_msg, new_r, pub)

    return {
        "message": "Redaction prepared — sign via MetaMask",
        "new_cid": new_cid,
        "new_r": hex(new_r),
        "new_ch_hash": new_ch_hash,
        "tx_data": tx_data,
        "record_id": record_id
    }


###############################################################
# ✅ 5) ACCESS REQUEST → tx_data
###############################################################
@router.post("/access-request")
async def access_request(
    doctor_address: str = Form(...),
    patient_address: str = Form(...),
    record_id: str = Form(...),
    role: int = Form(...),
    timestamp: int = Form(...),
    nonce: int = Form(...),
    sig_v: int = Form(...),
    sig_r: str = Form(...),
    sig_s: str = Form(...),
    ttl: int = Form(...)
):
    from blockchain_utils import get_record_by_id
    record = get_record_by_id(record_id)

    if not record["consent"]:
        raise HTTPException(400, detail="Consent inactive")

    tx_data = submit_access_request(
        doctor=doctor_address,
        patient=patient_address,
        record_id=record_id,
        role=role,
        timestamp=timestamp,
        nonce=nonce,
        v=sig_v,
        r=sig_r,
        s=sig_s,
        ttl=ttl
    )

    return {
        "message": "Access ready — sign via MetaMask",
        "tx_data": tx_data
    }


###############################################################
# ✅ 6) DOWNLOAD RECORD (returns decrypted PDF bytes)
###############################################################
@router.get("/download/{cid}")
async def download_ehr(cid: str):
    decrypted_bytes = download_from_ipfs(cid)

    return StreamingResponse(
        io.BytesIO(decrypted_bytes),
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{cid}.pdf"'}
    )

@router.get("/resolve/{patient_name}")
async def resolve_identity(patient_name: str):
    """
    Returns patient_address + record_id from chain.
    """
    from blockchain_utils import resolve_patient

    patient_address, record_id, idHashhex, idHashuint = resolve_patient(patient_name)
    print(patient_address, record_id, idHashhex, idHashuint)

    if not patient_address:
        raise HTTPException(status_code=404, detail="Patient not found")

    return {
        "patient_address": patient_address,
        "record_id": record_id,
        "idHashhex": idHashhex,
        "idHashuint": idHashuint
    }

@router.get("/requests")
async def requests_for_patient(patient_name: str):
    from blockchain_utils import resolve_patient
    from blockchain_utils import fetch_access_logs_for_patient
    import time

    patient_address, record_id, idHashhex, idHashuint = resolve_patient(patient_name)

    if not patient_address:
        raise HTTPException(status_code=404, detail="Patient not found")

    events = fetch_access_logs_for_patient(patient_address)
    now = int(time.time())

    formatted = []
    for ev in events:
        formatted.append({
            "doctor": ev.get("doctor_name") or ev.get("doctor_address"),
            "doctor_address": ev.get("doctor_address"),
            "patient": ev.get("patient_name") or ev.get("patient_address"),
            "record_id": ev["record_id"],
            "token": ev["token"],
            "expiresAt": ev["expiresAt"],
            "status": "approved" if ev["expiresAt"] >= now else "expired"
        })

    return {
        "patient": patient_address,
        "requests": formatted
    }

@router.get("/doctor/requests")
async def requests_for_doctor(doctor_addr: str):
    from blockchain_utils import fetch_access_logs_for_doctor
    import time

    events = fetch_access_logs_for_doctor(doctor_addr)
    now = int(time.time())

    formatted = []
    for ev in events:
        formatted.append({
            "patient": ev.get("patient_name") or ev.get("patient_address"),
            "patient_address": ev.get("patient_address"),
            "record_id": ev["record_id"],
            "token": ev["token"],
            "expiresAt": ev["expiresAt"],
            "status": "approved" if ev["expiresAt"] >= now else "expired"
        })

    return {
        "doctor": doctor_addr,
        "requests": formatted
    }

@router.get("/view/{record_id}")
async def view_ehr(
    record_id: str,
    doctor: str,
    token: str
):
    from blockchain_utils import check_token_valid, get_record_by_id
    import time

    # 1) Validate token
    if not check_token_valid(token):
        raise HTTPException(status_code=403, detail="Token expired")

    # 2) Fetch record details
    rec = get_record_by_id(record_id)
    if not rec:
        raise HTTPException(status_code=404, detail="Record not found")

    cid = rec.get("encryptedCid")
    if not cid:
        raise HTTPException(status_code=404, detail="CID missing")

    # 3) Fetch + decrypt
    decrypted = download_from_ipfs(cid)

    # 4) Stream only → inline view
    return StreamingResponse(
        io.BytesIO(decrypted),
        media_type="application/pdf",
        headers={"Content-Disposition": f'inline; filename="{record_id}.pdf"'}
    )

@router.post("/toggle-consent")
async def toggle_consent_endpoint(
    record_id: str = Form(...),
    eth_address: str = Form(...),
    active: bool = Form(...)
):
    """
    Build tx → MetaMask signs
    """
    from blockchain_utils import toggle_consent_tx

    tx_data = toggle_consent_tx(
        eth_address=eth_address,
        record_id=record_id,
        active=active
    )

    return {
        "message": "Consent toggle prepared — sign via MetaMask",
        "tx_data": tx_data
    }
