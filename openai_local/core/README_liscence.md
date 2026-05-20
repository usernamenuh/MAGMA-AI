# Core Security & Licensing Module

This directory contains the critical runtime components for the application's security and licensing system. These scripts are designed to be called by the main `run.sh` entrypoint *before* the main application starts, acting as a secure gatekeeper.

The logic here is intentionally decoupled from the main FastAPI application to ensure security checks are performed in a separate, controlled process.

---

## Files and Purpose

### `license_check.py`

*   **Role:** Standalone License Verifier.
*   **Function:** This is the primary security checkpoint. It performs a rigorous validation of the `license.lic` file found in the application's root directory.
*   **Execution:** It is the first script executed by the main `run.sh` entrypoint.
*   **Process:**
    1.  Loads the embedded `public_key.pem` to verify the license's cryptographic signature, ensuring it has not been tampered with.
    2.  Verifies that the license has not expired.
    3.  Calculates the current server's unique hardware fingerprint (Machine ID) and ensures it matches the ID that is cryptographically locked into the license.
*   **Output:**
    *   **On Success:** Prints the secret `data_key` (required for asset decryption) to standard output and exits with a status code of `0`.
    *   **On Failure:** Prints a descriptive error message to standard error and exits with a non-zero status code (`1`). This failure immediately halts the parent `run.sh` script and prevents the application from starting.

### `decrypt_files.py`

*   **Role:** Asset Decryption Utility.
*   **Function:** This script is responsible for decrypting the protected asset files (e.g., AI models, datasets) just before the application starts.
*   **Execution:** It is called by `run.sh` only *after* `license_check.py` has successfully executed and provided the `data_key`.
*   **Process:**
    1.  Receives a folder path and the `data_key` as command-line arguments.
    2.  Scans the specified folder for any files ending in the `.enc` extension.
    3.  Uses the `data_key` to decrypt each `.enc` file, writing the original, unencrypted file back to the disk and removing the encrypted version.
*   **Security Note:** This script performs decryption to the container's filesystem. This design allows the main application to function without modification. The primary security is enforced by the initial license check, which prevents the container from ever starting on unauthorized hardware.

### `public_key.pem`

*   **Role:** License Signature Verifier.
*   **Function:** This is the public half of a master cryptographic key pair. It is safely embedded within the application and is used exclusively to verify that a `license.lic` file was genuinely signed by the corresponding secret `private_key.pem` (which only the software vendor possesses). This mathematical relationship makes it impossible for a third party to forge a valid license.

---

## Build-Time Components Note

While this directory primarily contains runtime scripts, it's important to understand how the application's Python code is protected. This is handled by the `setup.py` script located in the project's root directory.

### `setup.py` (in project root)

*   **Role:** Build-time Code Compiler.
*   **Function:** This script is the engine for the code compilation security feature. It uses Cython to convert all human-readable Python (`.py`) files into secure, non-readable binary modules (`.so`).
*   **How it's run:** You do not run this script manually. It is automatically executed by the multi-stage `Dockerfile` during the image build process with the following command:
    ```bash
    python setup.py build_ext --inplace
    ```
*   **Process:** During the build, this script finds all Python source files, compiles them, and then securely deletes the originals, ensuring they are not included in the final, distributable Docker image. 