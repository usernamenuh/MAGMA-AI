import os
import sys
from cryptography.fernet import Fernet

def decrypt_folder(folder_path: str, data_key: str):
    """
    Walks a directory and decrypts every file ending in .enc.
    This is less secure than in-memory decryption as it leaves
    unencrypted files on the disk.
    """
    try:
        cipher = Fernet(data_key.encode('utf-8'))
    except Exception:
        print("FATAL: Invalid data key provided.", file=sys.stderr)
        sys.exit(1)

    decrypted_count = 0
    for root, _, files in os.walk(folder_path):
        for filename in files:
            if not filename.endswith(".enc"):
                continue

            encrypted_path = os.path.join(root, filename)
            decrypted_path = encrypted_path[:-4] # Remove .enc extension

            try:
                with open(encrypted_path, "rb") as f:
                    encrypted_data = f.read()
                
                decrypted_data = cipher.decrypt(encrypted_data)
                
                with open(decrypted_path, "wb") as f:
                    f.write(decrypted_data)
                
                # Optionally, remove the encrypted file after decryption
                os.remove(encrypted_path)
                decrypted_count += 1
            except Exception as e:
                print(f"WARN: Failed to decrypt {encrypted_path}. It might be corrupt. Error: {e}", file=sys.stderr)
    
    if decrypted_count > 0:
        print(f"✅ Decrypted {decrypted_count} file(s) in {folder_path}.")
    else:
        print(f"ℹ️ No files to decrypt in {folder_path}.")


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: python decrypt_files.py <folder_path> <data_key>", file=sys.stderr)
        sys.exit(1)
    
    folder_to_decrypt = sys.argv[1]
    key = sys.argv[2]
    
    decrypt_folder(folder_to_decrypt, key) 