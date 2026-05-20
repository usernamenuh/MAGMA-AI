import uuid
from pathlib import Path
from tinydb import TinyDB, Query

# Ensure db directory exists
Path("db").mkdir(exist_ok=True)

db = TinyDB("db/api_keys.json")
keys_table = db.table("keys")

def generate_api_key() -> str:
    """Generate and store a new API key"""
    new_key = uuid.uuid4().hex
    keys_table.insert({"key": new_key, "active": True})
    return new_key

def revoke_api_key(api_key: str):
    """Deactivate an API key"""
    Key = Query()
    keys_table.update({"active": False}, Key.key == api_key)

def validate_api_key(api_key: str) -> bool:
    """Check if API key is active"""
    print(api_key)
    Key = Query()
    result = keys_table.get((Key.key == api_key) & (Key.active == True))
    return result is not None
