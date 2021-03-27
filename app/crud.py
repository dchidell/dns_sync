from typing import List

from sqlalchemy.orm import Session

from . import models, schemas

# required to allow use of None (as NULL) as a specified value
sentinel = object()


def get_dns_records(
    db: Session, owner: str = sentinel, show_soft_deleted=True
) -> List[models.DNSRecord]:
    if not show_soft_deleted:
        q = db.query(models.DNSRecord).filter_by(to_delete=False)
    else:
        q = db.query(models.DNSRecord)

    if owner is not sentinel:
        return q.filter_by(owner=owner).all()

    return q.all()


def get_soft_deleted_dns_records(
    db: Session, owner: str = sentinel
) -> List[models.DNSRecord]:
    if owner is not sentinel:
        return db.query(models.DNSRecord).filter_by(owner=owner, to_delete=True).all()

    return db.query(models.DNSRecord).filter_by(to_delete=True).all()


def get_dns_by_name(db: Session, dns_name: str) -> models.DNSRecord:
    return db.query(models.DNSRecord).filter(models.DNSRecord.name == dns_name).first()


def _upsert_dns_record(db: Session, dns_record: schemas.DNSRecord) -> models.DNSRecord:
    dns_record = schemas.DNSRecordDB(**dns_record.dict())
    dns_name = dns_record.name
    db_dns_record = get_dns_by_name(db, dns_name=dns_name)
    if db_dns_record:
        for k, v in dns_record.dict().items():
            setattr(db_dns_record, k, v)
    else:
        db_dns_record = models.DNSRecord(**dns_record.dict())
        db.add(db_dns_record)

    return db_dns_record


def upsert_dns(db: Session, dns_record: schemas.DNSRecord) -> models.DNSRecord:
    db_dns_record = _upsert_dns_record(db, dns_record)
    db.commit()
    db.refresh(db_dns_record)
    return db_dns_record


def _upsert_dns_records(
    db: Session, dns_records: List[schemas.DNSRecord]
) -> List[models.DNSRecord]:
    return [_upsert_dns_record(db, dns_record) for dns_record in dns_records]


def upsert_dns_records(
    db: Session, dns_records: List[schemas.DNSRecord]
) -> List[models.DNSRecord]:
    db_dns_records = _upsert_dns_records(db, dns_records)

    db.commit()
    db.expire_all()  # ???
    return db_dns_records


def soft_delete_dns(db: Session, dns_name: str):
    db_dns_record = get_dns_by_name(db, dns_name)
    if not db_dns_record:
        raise ValueError(f'No record found for name: "{dns_name}"')
    db_dns_record.to_delete = True
    db.commit()


def delete_soft_deleted_records(db: Session, owner: str = sentinel):
    to_del = get_soft_deleted_dns_records(db=db, owner=owner)

    for record in to_del:
        db.delete(record)
    db.commit()


def delete_dns(db: Session, dns_name: str):
    db_dns_record = get_dns_by_name(db, dns_name)
    if not db_dns_record:
        raise ValueError(f'No record found for name: "{dns_name}"')
    db.delete(db_dns_record)
    db.commit()


def _soft_delete_all_dns_records(
    db: Session, owner: str = sentinel
) -> List[models.DNSRecord]:
    db_dns_records = get_dns_records(db, owner=owner)

    for db_dns_record in db_dns_records:
        db_dns_record.to_delete = True

    return db_dns_records


def _delete_all_dns_records(db: Session, owner: str = sentinel):
    db_dns_records = get_dns_records(db, owner=owner)

    for db_dns_record in db_dns_records:
        db.delete(db_dns_record)


def delete_all_dns_records(db: Session, owner: str = sentinel):
    _delete_all_dns_records(db, owner)

    db.commit()


def soft_delete_all_dns_records(db: Session, owner: str = sentinel):
    _soft_delete_all_dns_records(db, owner)

    db.commit()


def soft_sync_all_dns_records(
    db: Session,
    dns_records: List[schemas.DNSRecord],
    owner: str = sentinel,
) -> List[models.DNSRecord]:

    _soft_delete_all_dns_records(db, owner)
    db_dns_records = _upsert_dns_records(db, dns_records)

    db.commit()
    db.expire_all()  # ???
    return db_dns_records


def sync_all_dns_records(
    db: Session,
    dns_records: List[schemas.DNSRecord],
    owner: str = sentinel,
) -> List[models.DNSRecord]:

    _delete_all_dns_records(db, owner)
    db_dns_records = _upsert_dns_records(db, dns_records)

    db.commit()
    db.expire_all()  # ???
    return db_dns_records
