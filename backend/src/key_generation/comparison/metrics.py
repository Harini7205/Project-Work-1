# src/key_generation/comparison/metrics.py

def get_rsa_key_size_bytes(key_pair):
    """Returns the size of the RSA key pair in bytes."""
    private_key, public_key = key_pair
    # The size of the public key's modulus is the standard measure
    return private_key.key_size // 8

def get_ecc_metrics(key_pair, curve_name):
    """
    Returns a tuple of (key_size_bits, key_size_bytes) for a given ECC key.
    This function correctly handles all supported curve types.
    """
    private_key, public_key = key_pair

    # Handle the specific case for Curve25519 and Curve448
    if curve_name == "Curve25519":
        key_size_bits = 255
        key_size_bytes = 32
    elif curve_name == "Curve448":
        key_size_bits = 448
        key_size_bytes = 56
    else:
        # For all other curves (NIST, SEC), use the public_key.key_size attribute
        key_size_bits = public_key.key_size
        key_size_bytes = public_key.key_size // 8

    return key_size_bits, key_size_bytes

def get_equivalent_security_bits(size_or_curve, algo):
    """
    Returns the NIST-recommended symmetric security bit level for a given
    key size/curve, based on common industry standards.
    """
    # NIST SP 800-57 Part 1 Rev 5 (as of 2020)
    if algo == "RSA":
        if size_or_curve >= 7680: return 192
        if size_or_curve >= 3072: return 128
        if size_or_curve >= 2048: return 112
    elif algo == "ECC":
        # Check for specific curve names first
        if size_or_curve == "Curve25519": return 128  # Provides 128-bit security
        if size_or_curve == "Curve448": return 224    # Provides 224-bit security
        # Then, check for NIST curve bit sizes
        if size_or_curve == "SECP521R1": return 256
        if size_or_curve == "SECP384R1": return 192
        if size_or_curve == "SECP256R1": return 128
        if size_or_curve == "SECP256K1": return 128  # Commonly used in cryptocurrencies
    return "N/A"