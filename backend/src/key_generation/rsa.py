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

def get_rsa_key_size(key_pair):
    """Returns the size of the RSA key pair in bytes."""
    private_key, public_key = key_pair
    # The RSA key size is often expressed as the modulus size in bits.
    # We can get the size of the private key, which is the same as the public key's modulus.
    return private_key.key_size // 8