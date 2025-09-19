import os
import secrets
import time
from Crypto.Hash import SHA256, keccak
from coincurve import PublicKey

OUT_DIR = "outputs"
CID_FILE = os.path.join(OUT_DIR, "cid.txt")
CH_HASH_FILE = os.path.join(OUT_DIR, "ch_hash.hex")
R1_FILE = os.path.join(OUT_DIR, "r1.hex")
IDENTITY_FILE = os.path.join(OUT_DIR, "identity.hex")
PK_FILE = os.path.join(OUT_DIR, "pk.bin")

SECP256K1_N = int("FFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFEBAAEDCE6AF48A03BBFD25E8CD0364141", 16)

def _mod(a: int, m: int) -> int:
    r = a % m
    return r if r >= 0 else r + m

def _rand_scalar() -> int:
    while True:
        x = secrets.randbelow(SECP256K1_N)
        if 0 < x < SECP256K1_N:
            return x

def _sha256(b: bytes) -> bytes:
    h = SHA256.new()
    h.update(b)
    return h.digest()

def _keccak256(b: bytes) -> bytes:
    k = keccak.new(digest_bits=256)
    k.update(b)
    return k.digest()

def _hash_to_scalar(b: bytes) -> int:
    s = int.from_bytes(_sha256(b), "big") % SECP256K1_N
    return 1 if s == 0 else s

def encode_message(proof_bytes: bytes, cid_utf8: str, consent_active: bool, identity_bytes: bytes) -> bytes:
    tag = b"ZKID_CH_v1"
    proof_h = _keccak256(proof_bytes)
    cid_h = _keccak256(cid_utf8.encode("utf-8"))
    consent = b"\x01" if consent_active else b"\x00"
    return tag + proof_h + cid_h + consent + identity_bytes

def ch_hash(m_bytes: bytes, r: int, pk: PublicKey):
    m = _hash_to_scalar(m_bytes)
    mG = PublicKey.from_valid_secret(m.to_bytes(32, "big"))
    rY = pk.multiply(r.to_bytes(32, "big"))
    P = PublicKey.combine_keys([mG, rY])
    comp = P.format(compressed=True)
    h = _keccak256(comp).hex()
    return h, comp

# --- main ---
def main():
    os.makedirs(OUT_DIR, exist_ok=True)

    # 1) Check pk.bin
    if not os.path.exists(PK_FILE):
        print(f"ERROR: {PK_FILE} not found! Blockchain student must provide the ECC public key.")
        return
    pk_bytes = open(PK_FILE, "rb").read()
    if len(pk_bytes) != 33:
        print("ERROR: pk.bin must be 33 bytes (compressed public key)")
        return
    pk = PublicKey(pk_bytes)

    # 2) Read CID
    if not os.path.exists(CID_FILE):
        print(f"ERROR: {CID_FILE} not found! Run encrypt.py first.")
        return
    with open(CID_FILE, "r") as f:
        cid = f.read().strip()

    # 3) Load dummy proof (replace with PLONK proof later)
    proof = secrets.token_bytes(96)  # placeholder 96 bytes

    # 4) Identity bytes
    identity = pk.format(compressed=True)

    # 5) Build message and compute chameleon hash
    m1 = encode_message(proof, cid, True, identity)
    r1 = _rand_scalar()
    h1, _ = ch_hash(m1, r1, pk)

    # 6) Save outputs for blockchain student
    with open(CH_HASH_FILE, "w") as f:
        f.write(h1 + "\n")
    with open(R1_FILE, "w") as f:
        f.write(hex(r1) + "\n")
    with open(IDENTITY_FILE, "wb") as f:
        f.write(identity)

    print("✅ Chameleon hash computed:", h1)
    print("Randomness r1:", hex(r1))
    print("✅ Identity bytes saved for blockchain student")

if __name__ == "__main__":
    main()
