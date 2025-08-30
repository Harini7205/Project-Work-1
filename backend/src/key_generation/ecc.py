from cryptography.hazmat.primitives.asymmetric import ec

def generate_ecc_key_pair():
    """
    Generates an ECC private and public key pair for a given curve.
    Returns:
        tuple: A tuple containing the private key and public key objects.
    """
    # Use the chosen SECP256K1 curve
    private_key = ec.generate_private_key(ec.SECP256K1())
    public_key = private_key.public_key()
    return private_key, public_key
