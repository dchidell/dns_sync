from typing import Dict

from pydantic import BaseModel, BaseSettings


class DomainConfig(BaseModel):
    zone_id: str
    jwt: str


class Settings(BaseSettings):
    domain_config: Dict[str, DomainConfig]
    SQLALCHEMY_DATABASE_URL: str = "sqlite:////app/data/sqlite.db"
    BACKUP_FILE: str = '/app/data/backup.json'


settings = Settings()
