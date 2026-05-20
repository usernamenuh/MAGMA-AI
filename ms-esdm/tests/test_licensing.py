from unittest.mock import patch

import pytest
import json
import datetime
from licensing import service, fingerprint
from licensing.exceptions import LicenseInvalid
from licensing.sign import sign_license

# -----------------------------
# Helper: create license dict
# -----------------------------
def make_license(valid_from, valid_until):
    return {
        "license_id": "TEST-001",
        "max_users": 5,
        "max_machines": 2,
        "valid_from": valid_from.isoformat(),
        "valid_until": valid_until.isoformat(),
    }

# -----------------------------
# Fixture: temporary license file
# -----------------------------
@pytest.fixture
def temp_license_file(tmp_path):
    def _write(lic_dict):
        path = tmp_path / "license.json"
        with open(path, "w") as f:
            json.dump(lic_dict, f)
        return str(path)
    return _write

# -----------------------------
# Fixture: mock fingerprint
# -----------------------------
@pytest.fixture
def mock_fingerprint():
    with patch("licensing.fingerprint.get_machine_fingerprint", return_value="mock-fp"):
        yield

# -----------------------------
# Mock DB
# -----------------------------
class MockDB:
    def __init__(self):
        self.activated = set()

    def get_activated_machines(self):
        return self.activated

    def register_machine(self, fp):
        self.activated.add(fp)

# -----------------------------
# Test 1: Valid license
# -----------------------------
def test_valid_license(mock_fingerprint, temp_license_file):
    lic = make_license(datetime.datetime(2025,1,1), datetime.datetime(2030,1,1))
    signed_lic = sign_license(lic)
    path = temp_license_file(signed_lic)
    db = MockDB()

    ls = service.LicenseService(db, path)
    ls.validate_startup()
    ls.validate_request()
    status = ls.status()
    assert status["license_id"] == "TEST-001"
    assert status["max_users"] == 5
    assert status["max_machines"] == 2

# -----------------------------
# Test 2: Expired license
# -----------------------------
def test_expired_license(mock_fingerprint, temp_license_file):
    lic = make_license(datetime.datetime(2020,1,1), datetime.datetime(2021,1,1))
    signed_lic = sign_license(lic)
    path = temp_license_file(signed_lic)
    db = MockDB()

    ls = service.LicenseService(db, path)
    with pytest.raises(LicenseInvalid):
        ls.validate_startup()
    with pytest.raises(LicenseInvalid):
        ls.validate_request()

# -----------------------------
# Test 3: Bad signature
# -----------------------------
def test_bad_signature(mock_fingerprint, temp_license_file):
    lic = make_license(datetime.datetime(2025,1,1), datetime.datetime(2030,1,1))
    # tamper signature
    signed_lic = sign_license(lic)
    signed_lic["signature"] = "AAAA"  # invalid Base64 signature
    path = temp_license_file(signed_lic)
    db = MockDB()

    with pytest.raises(LicenseInvalid):
        service.LicenseService(db, path)

# -----------------------------
# Test 4: Machine limit exceeded
# -----------------------------
def test_machine_limit_exceeded(mock_fingerprint, temp_license_file):
    lic = make_license(datetime.datetime(2025,1,1), datetime.datetime(2030,1,1))
    signed_lic = sign_license(lic)
    path = temp_license_file(signed_lic)
    db = MockDB()
    db.activated.update({"fp1","fp2"})  # max_machines = 2

    ls = service.LicenseService(db, path)
    with pytest.raises(LicenseInvalid):
        ls.validate_startup()