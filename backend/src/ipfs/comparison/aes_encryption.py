from Crypto.Cipher import AES
from Crypto.Random import get_random_bytes
from hashlib import sha256

def encrypt_pdf(input_file: str, output_file: str, password: str):
    key = sha256(password.encode()).digest()  # 32 bytes key
    iv = get_random_bytes(16)
    
    cipher = AES.new(key, AES.MODE_CBC, iv)
    
    with open(input_file, "rb") as f:
        data = f.read()
    
    # Pad to multiple of 16
    padding_len = 16 - (len(data) % 16)
    data += bytes([padding_len]) * padding_len
    
    ciphertext = cipher.encrypt(data)
    
    with open(output_file, "wb") as f:
        f.write(iv + ciphertext)  # prepend IV

def decrypt_pdf(input_file: str, output_file: str, password: str):
    key = sha256(password.encode()).digest()
    
    with open(input_file, "rb") as f:
        iv = f.read(16)
        ciphertext = f.read()
    
    cipher = AES.new(key, AES.MODE_CBC, iv)
    data = cipher.decrypt(ciphertext)
    
    # Remove padding
    padding_len = data[-1]
    data = data[:-padding_len]
    
    with open(output_file, "wb") as f:
        f.write(data)

