from sqlalchemy import Boolean, Column, Integer, String

from .database import Base


class DNSRecord(Base):
    __tablename__ = 'dns_records'

    id = Column(Integer, primary_key=True, index=True)
    type = Column(String)
    name = Column(String, unique=True, index=True)  # should this be unique?
    content = Column(String)
    ttl = Column(String)
    proxied = Column(Boolean)
    owner = Column(String)
    to_delete = Column(Boolean)
