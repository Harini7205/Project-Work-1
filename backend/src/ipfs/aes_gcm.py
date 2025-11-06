# backend/src/ipfs/aes_gcm.py

from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from hashlib import sha256
import os
from dotenv import load_dotenv

load_dotenv()

# Optional: default password from ENV
DEFAULT_PASSWORD = os.environ.get("FILE_ENCRYPT_PASSWORD")


def _derive_key(password: str = "") -> bytes:
    """
    Derive 32-byte AES key using SHA-256.
    If no password is supplied, fallback to ENV password.
    """
    pwd = password or DEFAULT_PASSWORD
    if pwd is None:
        raise Exception("No AES password provided")

    return sha256(str(pwd).encode()).digest()   # 32 bytes → AES-256


#######################################################################
# ✅ In-memory encryption
#######################################################################
def encrypt_bytes(plaintext: bytes, password: str = "") -> bytes:
    """
    Encrypt bytes with AES-GCM.
    Returns nonce + ciphertext
    """
    key = _derive_key(password)
    aesgcm = AESGCM(key)

    nonce = os.urandom(12)
    ciphertext = aesgcm.encrypt(nonce, plaintext, None)

    return nonce + ciphertext


#######################################################################
# ✅ In-memory decryption
#######################################################################
def decrypt_bytes(bundle: bytes, password: str = "") -> bytes:
    """
    Decrypt nonce + ciphertext → plaintext
    """
    key = _derive_key(password)
    aesgcm = AESGCM(key)

    nonce = bundle[:12]
    ciphertext = bundle[12:]

    plaintext = aesgcm.decrypt(nonce, ciphertext, None)
    return plaintext
