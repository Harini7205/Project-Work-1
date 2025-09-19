from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives import serialization
from coincurve import PublicKey as CC_PublicKey
import os

def generate_ecc_key_pair():
    """
    Generates an ECC private and public key pair for SECP256K1 curve.
    Returns:
        tuple: private_key, public_key
    """
    private_key = ec.generate_private_key(ec.SECP256K1())
    public_key = private_key.public_key()
    return private_key, public_key

# --- generate keys ---
private_key, public_key = generate_ecc_key_pair()

# convert to coincurve PublicKey for ch_secp256k1.py
cc_pk = CC_PublicKey(public_key.public_bytes(
    encoding=serialization.Encoding.X962,
    format=serialization.PublicFormat.CompressedPoint
))

# save outputs folder
os.makedirs("outputs", exist_ok=True)

with open("outputs/pk.bin", "wb") as f:
    f.write(cc_pk.format(compressed=True))

# optionally save sk_int for yourself (hex)
sk_int = private_key.private_numbers().private_value
with open("outputs/sk_int.hex", "w") as f:
    f.write(hex(sk_int))

print("ECC key pair generated and saved to outputs/")
