from Crypto.Cipher import ARC4
from hashlib import sha256

def encrypt_pdf(input_file, output_file, password):
    key = sha256(password.encode()).digest()  # 256-bit derived
    cipher = ARC4.new(key)
    
    with open(input_file, "rb") as f:
        data = f.read()
    
    ct = cipher.encrypt(data)
    
    with open(output_file, "wb") as f:
        f.write(ct)

def decrypt_pdf(input_file, output_file, password):
    key = sha256(password.encode()).digest()
    cipher = ARC4.new(key)
    
    with open(input_file, "rb") as f:
        ct = f.read()
    
    data = cipher.decrypt(ct)
    
    with open(output_file, "wb") as f:
        f.write(data)
