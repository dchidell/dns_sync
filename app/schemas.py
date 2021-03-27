from enum import Enum

from pydantic import BaseModel, validator

from app.config import settings

domain_config = settings.domain_config


class Types(str, Enum):
    A = 'A'
    AAAA = 'AAAA'
    CNAME = 'CNAME'


class BaseDNSRecord(BaseModel):
    type: Types
    name: str
    content: str
    ttl: str
    proxied: bool

    @validator('name')
    def domain_is_setup(cls, v: str):
        if not v.endswith(tuple(domain_config)):
            raise ValueError(f'must end with a supported domain: {list(domain_config)}')
        return v

    @property
    def domain(self):
        for domain in domain_config:
            if self.name.endswith(domain):
                return domain

    @property
    def zone_id(self):
        return domain_config[self.domain].zone_id


class DNSRecord(BaseDNSRecord):
    owner: str

    class Config:
        orm_mode = True
        schema_extra = {
            'example': {
                'type': 'A',
                'name': 'example.com',
                'content': '0.0.0.0',
                'ttl': '1',
                'proxied': True,
                'owner': 'string',
            }
        }


class DNSRecordDB(DNSRecord):
    to_delete: bool = False


class DNSRecordCloudflare(BaseDNSRecord):
    id: str
