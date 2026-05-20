from sqlalchemy.orm import Session
from models.activated_machine import ActivatedMachine


class LicenseRepository:
    def __init__(self, engine):
        self.engine = engine

    def get_activated_machines(self):
        with Session(self.engine) as session:
            machines = session.query(ActivatedMachine).all()
            return [m.fingerprint for m in machines]

    def register_machine(self, fingerprint: str):
        with Session(self.engine) as session:
            machine = ActivatedMachine(fingerprint=fingerprint)
            session.add(machine)
            session.commit()