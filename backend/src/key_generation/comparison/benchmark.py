import time
import csv
import os

# Relative imports for the key generation algorithms
from .rsa import generate_rsa_key_pair
from .ecc import generate_ecc_key_pair

# Import all necessary functions from the metrics.py file
from .metrics import get_rsa_key_size_bytes, get_ecc_metrics, get_equivalent_security_bits

def run_key_generation_comparison(rsa_sizes, ecc_curves, num_runs=100):
    """
    Compares RSA and ECC key generation across different key sizes/curves.
    
    Args:
        rsa_sizes (list): A list of RSA key sizes to test (e.g., [2048, 3072]).
        ecc_curves (list): A list of ECC curve names to test (e.g., ["SECP256R1"]).
        num_runs (int): Number of times to run each test to get an average.
    """
    results = []

    print("Starting RSA key generation comparison...")
    for size in rsa_sizes:
        total_time = 0
        key_size_bytes = 0
        for _ in range(num_runs):
            start_time = time.time()
            priv, pub = generate_rsa_key_pair(key_size=size)
            end_time = time.time()
            total_time += (end_time - start_time)
            key_size_bytes = get_rsa_key_size_bytes((priv, pub))
        
        avg_time = total_time / num_runs

        results.append({
            "Algorithm": "RSA",
            "Key Size (bits)": size,
            "Key Size (bytes)": key_size_bytes,
            "Generation Time (s)": avg_time,
            "Equivalent Security (bits)": get_equivalent_security_bits(size, "RSA")
        })

    print("Starting ECC key generation comparison...")
    for curve in ecc_curves:
        total_time = 0
        key_size_bytes = 0
        curve_size_bits = 0
        for _ in range(num_runs):
            start_time = time.time()
            priv, pub = generate_ecc_key_pair(curve_name=curve)
            end_time = time.time()
            total_time += (end_time - start_time)
            curve_size_bits, key_size_bytes = get_ecc_metrics((priv, pub), curve)
            
        avg_time = total_time / num_runs
        
        results.append({
            "Algorithm": f"{curve} ECC",
            "Key Size (bits)": curve_size_bits,
            "Key Size (bytes)": key_size_bytes,
            "Generation Time (s)": avg_time,
            "Equivalent Security (bits)": get_equivalent_security_bits(curve, "ECC")
        })

    # Save results to a CSV file
    output_dir = "backend/src/key_generation/comparison/results"
    os.makedirs(output_dir, exist_ok=True)
    
    csv_file_path = f"{output_dir}/rsa_ecc_comparison.csv"
    with open(csv_file_path, "w", newline="") as f:
        fieldnames = ["Algorithm", "Key Size (bits)", "Key Size (bytes)", "Generation Time (s)", "Equivalent Security (bits)"]
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(results)

    print(f"Comparison complete. Results saved to {csv_file_path}")

if __name__ == "__main__":
    rsa_key_sizes = [2048, 3072, 4096]
    ecc_curves = ["SECP256R1", "SECP384R1", "SECP521R1", "SECP256K1", "Curve25519", "Curve448"]
    
    run_key_generation_comparison(rsa_key_sizes, ecc_curves)