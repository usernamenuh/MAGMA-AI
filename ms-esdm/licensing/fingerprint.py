import hashlib
import platform
import socket
from pathlib import Path


def _get_machine_id():
    machine_id_path = Path("/etc/machine-id")

    if machine_id_path.exists():
        return machine_id_path.read_text().strip()

    return f"{platform.node()}-{platform.system()}-{platform.processor()}"


def get_machine_fingerprint() -> str:
    raw = _get_machine_id() + socket.gethostname()
    return hashlib.sha256(raw.encode()).hexdigest()