from cryptography.hazmat.primitives.asymmetric import rsa

def generate_rsa_key_pair(key_size: int = 2048):
    """
    Generates an RSA private and public key pair.

    Args:
        key_size (int): The length of the key modulus in bits.
                        Common sizes: 2048, 3072, 4096.

    Returns:
        tuple: A tuple containing the private key and public key objects.
    """
    private_key = rsa.generate_private_key(
        public_exponent=65537,
        key_size=key_size,
    )
    public_key = private_key.public_key()
    return private_key, public_key
