from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from hashlib import sha256
import os

def encrypt_pdf(input_file, output_file, password):
    key = sha256(password.encode()).digest()  # 32 bytes
    aesgcm = AESGCM(key)
    nonce = os.urandom(12)
    
    with open(input_file, "rb") as f:
        data = f.read()
    
    ct = aesgcm.encrypt(nonce, data, None)
    
    with open(output_file, "wb") as f:
        f.write(nonce + ct)

def decrypt_pdf(input_file, output_file, password):
    key = sha256(password.encode()).digest()
    aesgcm = AESGCM(key)
    
    with open(input_file, "rb") as f:
        nonce = f.read(12)
        ct = f.read()
    
    data = aesgcm.decrypt(nonce, ct, None)
    
    with open(output_file, "wb") as f:
        f.write(data)
