import time
import os
import csv
from pathlib import Path

from aes_encryption import encrypt_pdf as encrypt_aes_cbc, decrypt_pdf as decrypt_aes_cbc
from aesgcm_encryption import encrypt_pdf as encrypt_aes_gcm, decrypt_pdf as decrypt_aes_gcm
from rc4_encryption import encrypt_pdf as encrypt_rc4, decrypt_pdf as decrypt_rc4
from metrics import calculate_entropy, byte_difference, chi_square_uniformity, byte_correlation

PASSWORD = "password123"
INPUT_FILE = "backend/src/inputs/sample.pdf"
OUT_DIR = Path("backend/src/ipfs/comparison/results")
OUT_DIR.mkdir(exist_ok=True)

NUM_RUNS = 10  # Number of runs to average metrics

def measure(encrypt_func, decrypt_func, algo_name):
    """Measure encryption/decryption metrics over multiple runs and return averages"""
    enc_file = OUT_DIR.joinpath(f"{algo_name}_enc.pdf")
    dec_file = OUT_DIR.joinpath(f"{algo_name}_dec.pdf")

    orig_size = os.path.getsize(INPUT_FILE)
    orig_bytes = open(INPUT_FILE, "rb").read()

    total_enc_time = 0
    total_dec_time = 0
    total_entropy = 0
    total_diff = 0
    enc_size = 0
    p = 0

    for _ in range(NUM_RUNS):
        # Encryption
        start = time.time()
        encrypt_func(INPUT_FILE, str(enc_file), PASSWORD)
        enc_time = time.time() - start
        total_enc_time += enc_time

        # Decryption
        start = time.time()
        decrypt_func(str(enc_file), str(dec_file), PASSWORD)
        dec_time = time.time() - start
        total_dec_time += dec_time

        enc_size = os.path.getsize(enc_file)
        enc_bytes = open(enc_file, "rb").read()

        total_entropy += calculate_entropy(enc_bytes)
        total_diff += byte_difference(orig_bytes, enc_bytes)
        p += chi_square_uniformity(enc_bytes)

    avg_enc_time = total_enc_time / NUM_RUNS
    avg_dec_time = total_dec_time / NUM_RUNS
    avg_entropy = total_entropy / NUM_RUNS
    avg_diff = total_diff / NUM_RUNS
    p /= NUM_RUNS

    return {
        "Algorithm": algo_name,
        "Original Size (bytes)": orig_size,
        "Encrypted Size (bytes)": enc_size,
        "Encryption Time (s)": round(avg_enc_time, 4),
        "Decryption Time (s)": round(avg_dec_time, 4),
        "Cipher Entropy (bits)": round(avg_entropy, 4),
        "Byte Difference": avg_diff,
        "Chi-Square p-value": round(p, 4)
    }

if __name__ == "__main__":
    results = []
    algorithms = [
        ("AES-256-CBC", encrypt_aes_cbc, decrypt_aes_cbc),
        ("AES-256-GCM", encrypt_aes_gcm, decrypt_aes_gcm),
        ("RC4", encrypt_rc4, decrypt_rc4)
    ]

    for name, enc_func, dec_func in algorithms:
        print(f"Running benchmark for {name}...")
        result = measure(enc_func, dec_func, name)
        results.append(result)

    # Save results to CSV
    csv_file_path = OUT_DIR / "encryption_comparison.csv"
    with open(csv_file_path, "w", newline="") as f:
        fieldnames = list(results[0].keys())
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(results)

    print(f"Encryption benchmark complete. Results saved to {csv_file_path}")
