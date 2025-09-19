import os
import sys
import subprocess
import argparse
from pathlib import Path

ECC_MODULE = "ecc"               
ENCRYPT_MODULE = "encrypt"       
CH_RUNNER = "ch_secp256k1.py"     
OUTDIR = Path("outputs")

def ensure_outdir():
    OUTDIR.mkdir(parents=True, exist_ok=True)

def generate_dummy_proof_if_missing(size=128):
    proof_path = OUTDIR / "proof.bin"
    if proof_path.exists():
        print(f"[ok] proof already exists: {proof_path}")
        return False
    print("[info] proof.bin not found — creating realistic dummy proof bytes")
    b = os.urandom(size)
    proof_path.write_bytes(b)
    # flag file so team knows it's synthetic
    (OUTDIR / "proof_generated.flag").write_text("GENERATED_DUMMY_PROOF\n")
    print(f"[wrote] {proof_path} ({size} bytes). Add real proof.bin later to replace.")
    return True

def run_module_function(module_name: str, func_name: str, *args, **kwargs):
    """
    Import module and call named function. Keeps calling environment in-process.
    If your modules are only runnable as scripts, you can instead call them via subprocess.
    """
    import importlib
    m = importlib.import_module(module_name)
    fn = getattr(m, func_name)
    return fn(*args, **kwargs)

def main(args):
    ensure_outdir()

    # 1) ECC keygen: attempt to call generate_ecc_key_pair() from ecc.py
    try:
        print("[step] running ECC key generation (ecc.generate_ecc_key_pair)...")
        sk, sk_int, pk = run_module_function(ECC_MODULE, "generate_ecc_key_pair")
        # try to save pk and optionally sk_int for demo (be careful w/ real keys)
        pk_bytes = pk.format(compressed=True)
        (OUTDIR / "pk.bin").write_bytes(pk_bytes)
        (OUTDIR / "sk_int.hex").write_text(hex(sk_int))
        print("[wrote] outputs/pk.bin and outputs/sk_int.hex (demo only; secure keys preferred)")
    except Exception as e:
        print(f"[error] ECC keygen failed: {e}", file=sys.stderr)
        print("If your ecc.py doesn't expose generate_ecc_key_pair(), run ecc.py separately and ensure outputs/pk.bin exists.")
        # continue or exit? we'll continue so you can still generate proof
        # return 2

    # 2) Encrypt + upload: call encrypt.encrypt_folder & upload_to_ipfs
    try:
        print("[step] encrypting and uploading to IPFS (encrypt.encrypt_folder & upload_to_ipfs)...")
        # adjust inputs as needed; these values can be changed via CLI
        input_folder = args.input_folder
        output_file = args.output_file
        password = args.password

        # call encrypt.encrypt_folder(input_folder, output_file, password)
        run_module_function(ENCRYPT_MODULE, "encrypt_folder", input_folder, output_file, password)
        cid = run_module_function(ENCRYPT_MODULE, "upload_to_ipfs", output_file)
        print("[ok] CID obtained:", cid)
        (OUTDIR / "cid.txt").write_text(cid)
        print("[wrote] outputs/cid.txt")
    except Exception as e:
        print(f"[error] encrypt/upload step failed: {e}", file=sys.stderr)
        print("If you prefer to run encrypt.py separately, ensure outputs/cid.txt exists and continue.")
        # continue anyway so we can still create dummy proof
        # return 3

    # 3) Ensure proof.bin exists; if not, create realistic dummy proof
    created = generate_dummy_proof_if_missing(size=args.dummy_proof_size)

    # 4) Run the chameleon hash runner script so it consumes outputs/* and writes ch_hash.hex
    # If your chameleon script is a module that we can import/call, you could import here.
    # For simplicity, run the script as a subprocess:
    if Path(CH_RUNNER).exists():
        print(f"[step] running chameleon runner: python {CH_RUNNER}")
        res = subprocess.run([sys.executable, CH_RUNNER], capture_output=False)
        print("[info] chameleon runner exited with code", res.returncode)
    else:
        print(f"[warn] {CH_RUNNER} not found. Please run your chameleon script (it should read outputs/ and produce ch_hash.hex).")

    print("\nDone. Files in outputs/:", sorted(p.name for p in OUTDIR.iterdir()))
    if created:
        print("NOTE: 'outputs/proof_generated.flag' indicates the proof was synthetic. Replace outputs/proof.bin with the real proof when available.")
    print("Blockchain student can now pick up outputs/ch_hash.hex and outputs/cid.txt to continue.")

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--input-folder", default=r"D:\secrete", help="folder to encrypt")
    ap.add_argument("--output-file", default="encrypted_folder.zip", help="encrypted output file")
    ap.add_argument("--password", default="Pavithra@123", help="zip password (demo only)")
    ap.add_argument("--dummy-proof-size", type=int, default=128, help="bytes length for generated dummy proof")
    args = ap.parse_args()
    main(args)
