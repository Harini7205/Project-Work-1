from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives.asymmetric import x25519, x448

def generate_ecc_key_pair(curve_name: str = "SECP256R1"):
    """
    Generates an ECC private and public key pair for a given curve.

    Args:
        curve_name (str): The name of the elliptic curve to use.
                          Common curves: SECP256R1, SECP384R1, SECP521R1, SECP256K1, Curve25519, Curve448.

    Returns:
        tuple: A tuple containing the private key and public key objects.
    """
    # Map common curve names to the cryptography library's curve objects
    curves = {
        "SECP256R1": ec.SECP256R1(),
        "SECP384R1": ec.SECP384R1(),
        "SECP521R1": ec.SECP521R1(),
        "SECP256K1": ec.SECP256K1(), # Used by Bitcoin
    }
    if curve_name == "Curve25519":
        private_key = x25519.X25519PrivateKey.generate()
        public_key = private_key.public_key()
    elif curve_name == "Curve448":
        private_key = x448.X448PrivateKey.generate()
        public_key = private_key.public_key()
    else:
        curve = curves.get(curve_name)
        if not curve:
            raise ValueError(f"Unknown curve name: {curve_name}")
        private_key = ec.generate_private_key(curve)
        public_key = private_key.public_key()
    return private_key, public_key

def get_ecc_key_size(key_pair):
    """Returns the size of the ECC key pair in bytes."""
    private_key, public_key = key_pair
    # ECC key size is the size of the curve's public key point in bytes.
    # The private key is a scalar of the same bit length as the curve.
    return public_key.key_size // 8