import os
import pyzipper
import requests

# --- Step 1: Encrypt Folder ---
def encrypt_folder(input_folder, output_file, password):
    with pyzipper.AESZipFile(output_file, 'w', compression=pyzipper.ZIP_LZMA) as zf:
        zf.setpassword(password.encode('utf-8'))
        zf.setencryption(pyzipper.WZ_AES, nbits=256)
        
        for foldername, subfolders, filenames in os.walk(input_folder):
            for filename in filenames:
                file_path = os.path.join(foldername, filename)
                arcname = os.path.relpath(file_path, input_folder)
                zf.write(file_path, arcname=arcname)

# --- Step 2: Upload Encrypted File to Private IPFS Node ---
def upload_to_ipfs(file_path, ipfs_api="http://127.0.0.1:5001/api/v0/add"):
    with open(file_path, "rb") as f:
        files = {"file": f}
        response = requests.post(ipfs_api, files=files)
        if response.status_code == 200:
            cid = response.json()["Hash"]
            return cid
        else:
            raise Exception(f"Failed to upload to IPFS: {response.text}")


if __name__ == "__main__":
    # Input/Output
    input_folder = r"D:\secrete"
    output_file = "encrypted_folder.zip"
    password = "Pavithra@123"   # must be 32 characters for AES-256
    
    # Step 1: Encrypt
    encrypt_folder(input_folder, output_file, password)
    #print(f"✅ Folder '{input_folder}' encrypted as '{output_file}'")

    # Step 2: Upload to Private IPFS
    try:
        cid = upload_to_ipfs(output_file)
        print(cid)
    except Exception as e:
        print(f"❌ Error: {e}")
