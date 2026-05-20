from datetime import datetime
from .schema import LicenseSchema
from .verify import verify_signature
from .fingerprint import get_machine_fingerprint
from .exceptions import LicenseInvalid
import json


class LicenseService:
    def __init__(self, db, license_path: str):
        self.db = db
        self.license_path = license_path
        self.license = self._load_license()

    def _load_license(self):
        with open(self.license_path) as f:
            data = json.load(f)

        if not verify_signature(data.copy()):
            raise LicenseInvalid("Invalid signature")

        return LicenseSchema(**data)

    def validate_startup(self):
        now = datetime.now()

        if now < self.license.valid_from:
            raise LicenseInvalid("License not active yet")

        if now > self.license.valid_until:
            raise LicenseInvalid("License expired")

        self._enforce_machine_limit()

    def _enforce_machine_limit(self):
        fingerprint = get_machine_fingerprint()

        machines = self.db.get_activated_machines()

        if fingerprint not in machines:
            if len(machines) >= self.license.max_machines:
                raise LicenseInvalid("Machine limit exceeded")

            self.db.register_machine(fingerprint)

    def validate_request(self):
        if datetime.now() > self.license.valid_until:
            raise LicenseInvalid("License expired")

    def status(self):
        return {
            "license_id": self.license.license_id,
            "valid_until": self.license.valid_until,
            "max_users": self.license.max_users,
            "max_machines": self.license.max_machines,
        }