from pydantic import BaseModel
from datetime import datetime


class LicenseSchema(BaseModel):
    license_id: str
    max_users: int
    max_machines: int
    valid_from: datetime
    valid_until: datetime
    signature: str