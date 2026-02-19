from fastapi import APIRouter, UploadFile, Form, HTTPException
from fastapi.responses import StreamingResponse
from web3 import Web3
import io, time, sqlite3, random, smtplib
from email.message import EmailMessage

# -------------------- IPFS + CRYPTO --------------------
from ipfs.ipfs_helper import upload_to_ipfs_bytes, download_from_ipfs_bytes as download_from_ipfs
from ipfs.aes_gcm import encrypt_bytes
from chameleon_hash.ch_secp256k1 import encode_message, ch_hash, _rand_scalar, forge_r
from key_generation.ecc import generate_ecc_key_pair

# -------------------- BLOCKCHAIN --------------------
from blockchain_utils import (
    register_identity,
    store_record,
    update_record,
    submit_access_request,
    get_record_by_id,
    get_record_id_by_owner,
    fetch_access_logs_for_patient,
    fetch_access_logs_for_doctor,
    check_token_valid,
    toggle_consent_tx
)
from dotenv import load_dotenv
import os

load_dotenv()

router = APIRouter(prefix="/ehr", tags=["EHR"])

EMAIL = str(os.getenv("EMAIL"))
PASSWORD = str(os.getenv("EMAIL_PASSWORD"))

# ======================================================
# DATABASE
# ======================================================
def get_db():
    conn = sqlite3.connect("auth.db", check_same_thread=False)
    conn.execute("PRAGMA journal_mode=WAL;")
    return conn

# ======================================================
# AUTH — EMAIL OTP (PATIENT + DOCTOR)
# ======================================================
@router.post("/auth/request-otp")
def request_otp(email: str = Form(...)):
    code = str(random.randint(100000, 999999))
    expires = int(time.time()) + 300

    db = get_db()
    db.execute("DELETE FROM otp WHERE email=?", (email,))
    db.execute("INSERT INTO otp VALUES (?,?,?)", (email, code, expires))
    db.commit()

    msg = EmailMessage()
    msg.set_content(f"Your OTP is {code}")
    msg["Subject"] = "EHR Login OTP"
    msg["To"] = email

    print(EMAIL, PASSWORD)

    with smtplib.SMTP("smtp.gmail.com", 587) as s:
        s.starttls()
        s.login(EMAIL,PASSWORD)
        s.send_message(msg)

    return {"message": "OTP sent"}

@router.post("/auth/verify-otp")
def verify_otp(
    email: str = Form(...),
    otp: str = Form(...),
    wallet: str = Form(...),
    role: str = Form(...)
):
    db = get_db()
    row = db.execute(
        "SELECT code, expires FROM otp WHERE email=?", (email,)
    ).fetchone()

    if not row or row[0] != otp or row[1] < time.time():
        raise HTTPException(401, "Invalid OTP")
    
    import uuid

    patient_id = "PID-" + uuid.uuid4().hex[:10].upper()


    db.execute("""
INSERT OR REPLACE INTO users(patient_id, email, wallet, role, verified)
VALUES (?,?,?,?,1)
""", (patient_id, email, wallet, role))

    db.execute("DELETE FROM otp WHERE email=?", (email,))
    db.commit()

    return {"message": "Login successful"}

# ======================================================
# KEY GENERATION
# ======================================================
@router.post("/generate-keys")
def generate_keys():
    sk, pk = generate_ecc_key_pair(save_to_disk=False)

    from cryptography.hazmat.primitives import serialization
    pub_bytes = pk.public_bytes(
        encoding=serialization.Encoding.X962,
        format=serialization.PublicFormat.CompressedPoint
    )

    return {
        "private_key": sk.private_numbers().private_value.to_bytes(32, "big").hex(),
        "public_key": pub_bytes.hex()
    }

# ======================================================
# REGISTER IDENTITY (ON-CHAIN)
# ======================================================
@router.post("/register")
def register_identity_api(
    public_key_hex: str = Form(...),
    eth_address: str = Form(...)
):
    tx_data = register_identity(
        eth_address=eth_address,
        pubkey_bytes=bytes.fromhex(public_key_hex)
    )

    return {
        "message": "Sign transaction in MetaMask",
        "tx_data": tx_data
    }

# ======================================================
# EHR FLOW
# ======================================================
@router.post("/encrypt")
async def encrypt_ehr(file: UploadFile):
    encrypted = encrypt_bytes(await file.read())
    return StreamingResponse(io.BytesIO(encrypted), media_type="application/octet-stream")

@router.post("/ipfs-upload")
async def upload_ipfs(file: UploadFile):
    cid = upload_to_ipfs_bytes(await file.read())
    return {"cid": cid}

@router.post("/chameleon-hash/{cid}")
def compute_ch(cid: str, public_key_hex: str = Form(...)):
    msg = encode_message(cid, True, bytes.fromhex(public_key_hex))
    r = _rand_scalar()
    ch_hex, _ = ch_hash(msg, r, bytes.fromhex(public_key_hex))
    return {"ch": ch_hex, "r": hex(r)}

@router.post("/store-record")
def store_record_endpoint(
    cid: str = Form(...),
    ch: str = Form(...),
    eth_address: str = Form(...)
):
    record_id = Web3.keccak(text=cid + eth_address).hex()
    tx_data = store_record(eth_address, record_id, ch, cid, True)

    return {"record_id": record_id, "tx_data": tx_data}

@router.post("/redact")
def redact_ehr(
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
    new_cid = upload_to_ipfs_bytes(file.file.read())

    pub = bytes.fromhex(public_key_hex)
    sk = int(private_key_hex, 16)
    old_r = int(old_r_hex, 16)

    old_msg = encode_message(old_cid, consent_active, pub)
    new_msg = encode_message(new_cid, consent_active, pub)

    new_r = forge_r(old_r, sk, old_msg, new_msg)
    tx_data = update_record(eth_address, record_id, new_cid, c_hash)

    return {
        "new_cid": new_cid,
        "new_r": hex(new_r),
        "tx_data": tx_data
    }

# ======================================================
# ACCESS REQUEST (DOCTOR → PATIENT via EMAIL)
# ======================================================
@router.post("/access-request")
def access_request(
    doctor_address: str = Form(...),
    patient_id: str = Form(...),
    role: int = Form(...),
    timestamp: int = Form(...),
    nonce: int = Form(...),
    sig_v: int = Form(...),
    sig_r: str = Form(...),
    sig_s: str = Form(...),
    ttl: int = Form(...)
):
    db = get_db()

    # 1️⃣ Resolve patient wallet from patient_id
    row = db.execute(
        "SELECT wallet FROM users WHERE patient_id=? AND role='patient'",
        (patient_id,)
    ).fetchone()

    if not row:
        raise HTTPException(status_code=404, detail="Patient not found")

    patient_address = row[0]

    # 2️⃣ Resolve record_id ON-CHAIN
    record_id = get_record_id_by_owner(patient_address)
    print("Resolved record_id:", record_id)

    if not record_id or record_id == "0000000000000000000000000000000000000000000000000000000000000000":
        raise HTTPException(
            status_code=404,
            detail="No record found for patient"
        )

    # 3️⃣ Fetch record + consent check
    record = get_record_by_id(record_id)

    if not record["consent"]:
        raise HTTPException(
            status_code=400,
            detail="Consent inactive"
        )

    # 4️⃣ Submit access request tx
    tx_data = submit_access_request(
        doctor_address,
        patient_address,
        record_id,
        role,
        timestamp,
        nonce,
        sig_v,
        sig_r,
        sig_s,
        ttl
    )

    return {
        "tx_data": tx_data,
        "record_id": record_id  # optional (for logs/UI)
    }


# ======================================================
# REQUEST LISTING
# ======================================================
@router.get("/requests/patient")
def patient_requests(email: str):
    db = get_db()
    wallet = db.execute(
        "SELECT wallet FROM users WHERE email=?", (email,)
    ).fetchone()

    if not wallet:
        raise HTTPException(404, "User not found")
    
    return {"requests": fetch_access_logs_for_patient(wallet[0])}

@router.get("/requests/doctor")
def doctor_requests(wallet: str):
    db = get_db()
    logs = fetch_access_logs_for_doctor(wallet)
    now = int(time.time())
    result = []

    for ev in logs:
        patient_address = Web3.to_checksum_address(ev["args"]["patient"]).lower()
        print("Patient address from event:", patient_address)

        row = db.execute(
            "SELECT patient_id FROM users WHERE wallet=? AND role='patient'",
            (patient_address,)
        ).fetchone()

        expires_at = int(ev["args"]["expiresAt"])
        print("Access request expires at:", expires_at, "Current time:", now)

        if expires_at > now:
            status = "approved"
        else:
            status = "expired"

        result.append({
            "doctor_address": ev["args"]["provider"],
            "patient_address": patient_address,
            "patient_id": row[0] if row else None,   # ✅ ADD THIS
            "record_id": "0x" + ev["args"]["recordId"].hex(),
            "token": "0x" + ev["args"]["token"].hex(),
            "expiresAt": int(ev["args"]["expiresAt"]),
            "status": status
        })

    print(result)
    return result

# ======================================================
# VIEW + CONSENT
# ======================================================
@router.get("/view/{record_id}")
def view_ehr(record_id: str, token: str):
    if not check_token_valid(token):
        raise HTTPException(403, "Token expired")

    rec = get_record_by_id(record_id)
    data = download_from_ipfs(rec["encryptedCid"])

    return StreamingResponse(io.BytesIO(data), media_type="application/pdf")

@router.post("/toggle-consent")
def toggle_consent(record_id: str = Form(...), eth_address: str = Form(...), active: bool = Form(...)):
    tx_data = toggle_consent_tx(eth_address, record_id, active)
    return {"tx_data": tx_data}

@router.get("/download/{cid}")
async def download_ehr(cid: str):
    decrypted_bytes = download_from_ipfs(cid)

    return StreamingResponse(
        io.BytesIO(decrypted_bytes),
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{cid}.pdf"'}
    )

@router.get("/resolve-patient/{patient_id}")
def resolve_patient(patient_id: str):
    db = get_db()
    print("Resolving patient_id:", patient_id)

    row = db.execute(
        """
        SELECT wallet FROM users
        WHERE patient_id=? AND role='patient'
        """,
        (patient_id,)
    ).fetchone()

    if not row:
        raise HTTPException(404, "Patient not found")

    patient_address = Web3.to_checksum_address(row[0])

    # get latest record id from blockchain
    record_id = get_record_id_by_owner(patient_address)

    if not record_id or int(record_id, 16) == 0:
        raise HTTPException(404, "No record found")

    return {
        "patient_address": patient_address,
        "record_id": record_id
    }
