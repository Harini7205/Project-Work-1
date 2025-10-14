# backend/src/key_generation/ecc.py
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives import serialization
import os

OUT_DIR = os.path.join(os.path.dirname(__file__), "..", "outputs")
os.makedirs(OUT_DIR, exist_ok=True)

def generate_ecc_key_pair(save_to_disk=True):
    """
    Generates ECC private and public key pair (SECP256K1).
    If save_to_disk is True, writes:
      - pk.bin (compressed public key, 33 bytes)
      - sk.hex (private scalar hex)
    Returns (private_key_obj, public_key_obj)
    """
    private_key = ec.generate_private_key(ec.SECP256K1())
    public_key = private_key.public_key()

    if save_to_disk:
        # private scalar in hex
        private_bytes = private_key.private_numbers().private_value.to_bytes(32, "big")
        with open(os.path.join(OUT_DIR, "sk.hex"), "w") as f:
            f.write(private_bytes.hex())

        # compressed public key (33 bytes) in SEC1 format
        compressed_pub = public_key.public_bytes(
            encoding=serialization.Encoding.X962,
            format=serialization.PublicFormat.CompressedPoint
        )
        with open(os.path.join(OUT_DIR, "pk.bin"), "wb") as f:
            f.write(compressed_pub)

    return private_key, public_key
