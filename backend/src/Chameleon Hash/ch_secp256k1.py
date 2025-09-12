import secrets, time
from typing import Tuple
from Crypto.Hash import SHA256, keccak
from coincurve import PrivateKey, PublicKey

# secp256k1 group order n
SECP256K1_N = int("FFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFEBAAEDCE6AF48A03BBFD25E8CD0364141", 16)
SECP256K1_KNOWN_N = SECP256K1_N

def _mod(a: int, m: int) -> int:
    r = a % m
    return r if r >= 0 else r + m

def _rand_scalar() -> int:
    while True:
        x = secrets.randbelow(SECP256K1_N)
        if 0 < x < SECP256K1_N:
            return x

def _sha256(b: bytes) -> bytes:
    h = SHA256.new(); h.update(b); return h.digest()

def _keccak256(b: bytes) -> bytes:
    k = keccak.new(digest_bits=256); k.update(b); return k.digest()

def _hash_to_scalar(b: bytes) -> int:
    s = int.from_bytes(_sha256(b), "big") % SECP256K1_N
    return 1 if s == 0 else s

def keygen() -> Tuple[PrivateKey, int, PublicKey]:
    sk_obj = PrivateKey()
    sk_int = int.from_bytes(sk_obj.secret, "big")  # integer form
    pk = sk_obj.public_key
    return sk_obj, sk_int, pk

def encode_message(
    proof_bytes: bytes,
    cid_utf8: str,
    consent_active: bool,
    identity_bytes: bytes
) -> bytes:
    tag = b"ZKID_CH_v1"
    proof_h = _keccak256(proof_bytes)
    cid_h = _keccak256(cid_utf8.encode("utf-8"))
    consent = b"\x01" if consent_active else b"\x00"
    return tag + proof_h + cid_h + consent + identity_bytes

def ch_hash(m_bytes: bytes, r: int, pk: PublicKey):
    m = _hash_to_scalar(m_bytes)
    # m*G
    mG = PublicKey.from_valid_secret(m.to_bytes(32, "big"))
    # r*Y
    rY = pk.multiply(r.to_bytes(32, "big"))
    # P = mG + rY
    P = PublicKey.combine_keys([mG, rY])
    comp = P.format(compressed=True)   # 33B
    h = _keccak256(comp).hex()         # 32B digest (hex string)
    return h, comp

def find_collision_r(m_bytes: bytes, r: int, m_bytes_prime: bytes, sk_int: int) -> int:
    m  = _hash_to_scalar(m_bytes)
    m2 = _hash_to_scalar(m_bytes_prime)
    inv_x = pow(sk_int, -1, SECP256K1_N)
    delta = _mod(m - m2, SECP256K1_N)
    return _mod(r + delta * inv_x, SECP256K1_KNOWN_N)

if __name__ == "__main__":
    # 1) keygen
    sk_obj, sk_int, pk = keygen()
    identity = pk.format(compressed=True)  # use ECC Q as identity bytes (33B)

    # 2) placeholder ZoKrates proof
    proof = bytes([7]) * 96
    cid = "bafy...example"

    # Build m1 (consent = active)
    m1 = encode_message(proof, cid, True, identity)
    r1 = _rand_scalar()

    t0 = time.perf_counter()
    h1, p1 = ch_hash(m1, r1, pk)
    t1 = time.perf_counter()

    # Build m2 (consent toggled to inactive) and compute r2 collision
    m2 = encode_message(proof, cid, False, identity)
    t2 = time.perf_counter()
    r2 = find_collision_r(m1, r1, m2, sk_int)  # pass int, not object
    t3 = time.perf_counter()

    h2, p2 = ch_hash(m2, r2, pk)
    t4 = time.perf_counter()

    print("Collision OK? ", h1 == h2)
    print("h:", h1)
    print(f"Hash time (m,r)->h: {(t1 - t0)*1e3:.3f} ms")
    print(f"Collision r' compute: {(t3 - t2)*1e3:.3f} ms")
    print(f"Re-hash time (m',r')->h: {(t4 - t3)*1e3:.3f} ms")
    print("Randomness r1:", hex(r1))
    print("Collision randomness r2:", hex(r2))

