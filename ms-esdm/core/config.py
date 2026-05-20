import os
from typing import List


class Settings:

    def __init__(self):
        # Example in .env: DOMAIN_EMAIL=@esdm.gov.id,@esdm.go.id,@tagflow-ai.com
        self.DOMAIN_EMAIL = os.getenv("DOMAIN_EMAIL", "@esdm.gov.id,@esdm.go.id,@tagflow-ai.com")

    @property
    def allowed_domains(self):
        items = [d.strip() for d in self.DOMAIN_EMAIL.split(",")]
        return [d if d.startswith("@") else f"@{d}" for d in items]

    DATABASE_URL = os.getenv("DATABASE_URL", "postgresql+asyncpg://esdm_user:password@localhost:5432/esdm_db")
    SYNC_DATABASE_URL = os.getenv("SYNC_DATABASE_URL", "postgresql+psycopg2://esdm_user:password@localhost:5432/esdm_db")
    JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "secret_key")
    JWT_REFRESH_SECRET_KEY = os.getenv("JWT_REFRESH_SECRET_KEY", "refresh_secret_key")
    AUTH_API_BASE_URL = os.getenv("AUTH_API_BASE_URL", "")
    EMBEDDING_PROVIDER = "fastembed"
    FASTEMBED_MODEL = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"

settings = Settings()
