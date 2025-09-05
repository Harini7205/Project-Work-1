import os
import pyzipper
def encrypt_folder(input_folder, output_file, password):
    with pyzipper.AESZipFile(output_file, 'w', compression=pyzipper.ZIP_LZMA) as zf:
        zf.setpassword(password.encode('utf-8'))
        zf.setencryption(pyzipper.WZ_AES, nbits=256)
        
        for foldername, subfolders, filenames in os.walk(input_folder):
            for filename in filenames:
                file_path = os.path.join(foldername, filename)
                arcname = os.path.relpath(file_path, input_folder)
                zf.write(file_path, arcname=arcname)
if __name__ == "__main__":
    input_folder = 'D:\secrete'
    output_file = 'encrypted_folder.zip'
    # Password must be 32 bytes (256-bit) long
    password = 'Pavithra@123'
    encrypt_folder(input_folder, output_file, password)
    print(f"Folder '{input_folder}' has been encrypted as '{output_file}'")