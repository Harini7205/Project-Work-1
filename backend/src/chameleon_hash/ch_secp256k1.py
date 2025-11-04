# backend/src/chameleon_hash.py
import os
import secrets
from Crypto.Hash import SHA256, keccak
from coincurve import PublicKey

OUT_DIR = os.path.join(os.path.dirname(__file__), "outputs")
os.makedirs(OUT_DIR, exist_ok=True)

# secp256k1 order
SECP256K1_N = int("FFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFEBAAEDCE6AF48A03BBFD25E8CD0364141", 16)

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

def _rand_scalar() -> int:
    while True:
        x = secrets.randbelow(SECP256K1_N)
        if 0 < x < SECP256K1_N:
            return x

def encode_message(cid_utf8: str, consent_active: bool, identity_bytes: bytes) -> bytes:
    tag = b"ZKID_CH_v1"
    cid_h = _keccak256(cid_utf8.encode("utf-8"))
    consent = b"\x01" if consent_active else b"\x00"
    return tag + cid_h + consent + identity_bytes

def ch_hash(m_bytes: bytes, r: int, pk_pubbytes: bytes):
    """
    Compute chameleon hash H = keccak256( (r*G + H(m)*P).compressed )
    pk_pubbytes: compressed public key bytes (33 bytes)
    """
    # 1) H(m) as scalar
    hm = _hash_to_scalar(m_bytes)
    # 2) r*G -> create PublicKey from secret r (r*G)
    rG = PublicKey.from_valid_secret(r.to_bytes(32, "big"))
    # 3) hm * P => multiply public key P by scalar hm
    P = PublicKey(pk_pubbytes)
    hmP = P.multiply(hm.to_bytes(32, "big"))
    # 4) add points rG + hmP
    # combine_keys can add arbitrary public keys
    S = PublicKey.combine_keys([rG, hmP])
    comp = S.format(compressed=True)  # 33 bytes
    digest = _keccak256(comp).hex()
    return digest, comp

def forge_r(original_r: int, trapdoor_x: int, original_message: bytes, new_message: bytes) -> int:
    """
    Given trapdoor x (private scalar such that P = x*G), compute r' s.t.
    r'*G + H(m')*P = r*G + H(m)*P
    => r' = r + x*(H(m) - H(m')) mod n
    """
    H_orig = _hash_to_scalar(original_message)
    H_new = _hash_to_scalar(new_message)
    delta = (H_orig - H_new) % SECP256K1_N
    r_new = (original_r + (trapdoor_x * delta)) % SECP256K1_N
    return r_new
