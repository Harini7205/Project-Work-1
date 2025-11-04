# backend/src/ipfs/ipfs_helper.py
import os
import requests
from pathlib import Path

from .aes_gcm import encrypt_pdf, decrypt_pdf  # Assuming this is the AES-GCM module

OUT_FILE = Path("ipfs/temporary")
os.makedirs(OUT_FILE, exist_ok=True)

def upload_to_ipfs(input_file: str, ipfs_api="http://127.0.0.1:5001/api/v0/add") -> str:
    """Upload a file to a local IPFS HTTP API. Returns CID string."""
    temp_file = OUT_FILE.joinpath("encrypted_file.pdf")
    encrypt_pdf(input_file, temp_file)
    with open(temp_file, "rb") as f:
        files = {"file": f}
        response = requests.post(ipfs_api, files=files, timeout=60)
        if response.status_code == 200:
            return response.json()["Hash"]
        else:
            raise Exception(f"Failed to upload to IPFS: {response.status_code} {response.text}")

def download_from_ipfs(cid: str, output_file: str, ipfs_gateway="http://127.0.0.1:8080/ipfs/"):
    """
    Download a file from IPFS given its CID and save it to output_file.
    """
    url = f"{ipfs_gateway}{cid}"
    response = requests.get(url, timeout=60)
    temp_file = OUT_FILE.joinpath("downloaded_file.pdf")
    if response.status_code == 200:
        with open(temp_file, "wb") as f:
            f.write(response.content)
        print(f"Downloaded CID {cid} to {temp_file}")
        decrypt_pdf(temp_file, output_file)  
        print(f"Decrypted file saved to: {output_file}")
    else:
        raise Exception(f"Failed to download from IPFS: {response.status_code} {response.text}")
