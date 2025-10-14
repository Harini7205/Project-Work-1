#backend/src/ipfs/aes_gcm.py

from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from hashlib import sha256
import os
from dotenv import load_dotenv

load_dotenv()
password = os.environ.get("FILE_ENCRYPT_PASSWORD")
if password is None:
    raise Exception("Set env variable FILE_ENCRYPT_PASSWORD")

def encrypt_pdf(input_file, output_file):
    key = sha256(str(password).encode()).digest()  # 32 bytes
    aesgcm = AESGCM(key)
    nonce = os.urandom(12)
    
    with open(input_file, "rb") as f:
        data = f.read()
    
    ct = aesgcm.encrypt(nonce, data, None)
    
    with open(output_file, "wb") as f:
        f.write(nonce + ct)

def decrypt_pdf(input_file, output_file):
    key = sha256(str(password).encode()).digest()
    aesgcm = AESGCM(key)
    
    with open(input_file, "rb") as f:
        nonce = f.read(12)
        ct = f.read()
    
    data = aesgcm.decrypt(nonce, ct, None)
    
    with open(output_file, "wb") as f:
        f.write(data)
