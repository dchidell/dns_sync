import logging
from typing import List, Union

import httpx
from fastapi import Depends, FastAPI, HTTPException, BackgroundTasks
from fastapi_utils.tasks import repeat_every
from sqlalchemy.orm import Session

from . import crud, models, schemas, cloudflare
from .config import settings
from .database import get_db, _get_fastapi_sessionmaker

logging.basicConfig(
    format="%(asctime)s - %(process)s - %(name)s - %(lineno)d - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

session_maker = _get_fastapi_sessionmaker()
models.Base.metadata.create_all(bind=session_maker.cached_engine)

app = FastAPI()


def write_dns_to_file(db: Session):
    db_records = crud.get_dns_records(db, show_soft_deleted=False)
    json_records = [schemas.DNSRecordDB.from_orm(record).json() for record in db_records]

    # make file name an env var
    with open(settings.BACKUP_FILE, 'w') as f:
        f.write('\n'.join(json_records))
        f.write('\n')


@app.on_event("startup")
@repeat_every(seconds=30, logger=logger, wait_first=True)
async def run_sync_with_cloudflare() -> None:
    logger.info('Starting Cloudflare Sync')
    with session_maker.context_session() as db:
        await sync_with_cloudflare(db=db)
    logger.info('Finished Cloudflare Sync')


async def sync_with_cloudflare(db: Session):
    dns_records_db = crud.get_dns_records(db)
    dns_records_db = [schemas.DNSRecordDB.from_orm(dns) for dns in dns_records_db]
    async with httpx.AsyncClient(base_url=cloudflare.BASE_URL) as client:
        await cloudflare.sync_dns_records(dns_records_db, client=client)

    crud.delete_soft_deleted_records(db=db)


@app.get('/dns-records', response_model=List[schemas.DNSRecordDB])
def get_dns_records(db: Session = Depends(get_db)):
    return crud.get_dns_records(db=db)


@app.get('/owner/{owner_name}/dns-records', response_model=List[schemas.DNSRecordDB])
def get_owner_dns_records(owner_name: str, db: Session = Depends(get_db)):
    return crud.get_dns_records(db=db, owner=owner_name)


@app.get('/dns-records/{dns_name}', response_model=schemas.DNSRecordDB)
def get_dns_record(dns_name: str, db: Session = Depends(get_db)):
    dns_record = crud.get_dns_by_name(db=db, dns_name=dns_name)
    if dns_record is None:
        raise HTTPException(status_code=404, detail="DNS Record not found")
    return dns_record


@app.delete('/dns-records/{dns_name}')
def delete_dns_record(dns_name: str, background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    try:
        crud.soft_delete_dns(db=db, dns_name=dns_name)
    except ValueError:
        raise HTTPException(status_code=404, detail="DNS Record not found")
    background_tasks.add_task(write_dns_to_file, db)
    return {'deleted': True}


@app.patch('/dns-records', response_model=Union[schemas.DNSRecord, List[schemas.DNSRecord]])
def upsert_dns_record(
        dns_record: Union[schemas.DNSRecord, List[schemas.DNSRecord]],
        background_tasks: BackgroundTasks,
        db: Session = Depends(get_db),
):
    if isinstance(dns_record, list):
        db_dns_record = crud.upsert_dns_records(db=db, dns_records=dns_record)
    else:
        db_dns_record = crud.upsert_dns(db=db, dns_record=dns_record)

    background_tasks.add_task(write_dns_to_file, db)
    return db_dns_record


@app.put('/dns-records', response_model=List[schemas.DNSRecord])
def replace_dns_records(
        dns_record: List[schemas.DNSRecord],
        background_tasks: BackgroundTasks,
        db: Session = Depends(get_db),
):
    db_dns_record = crud.soft_sync_all_dns_records(db=db, dns_records=dns_record)

    background_tasks.add_task(write_dns_to_file, db)
    return db_dns_record


@app.put('/owner/{owner_name}/dns-records', response_model=List[schemas.DNSRecord])
def replace_dns_records_owner(
        owner_name: str,
        dns_record: List[schemas.DNSRecord],
        background_tasks: BackgroundTasks,
        db: Session = Depends(get_db),
):

    db_dns_record = crud.soft_sync_all_dns_records(db=db, dns_records=dns_record, owner=owner_name)
    background_tasks.add_task(write_dns_to_file, db)
    return db_dns_record


@app.delete('/owner/{owner_name}/dns-records')
def delete_dns_records_owner(
        owner_name: str,
        background_tasks: BackgroundTasks,
        db: Session = Depends(get_db),
):
    crud.soft_delete_all_dns_records(db, owner=owner_name)
    background_tasks.add_task(write_dns_to_file, db)
    return {'deleted': True}


@app.delete('/dns-records')
def delete_dns_records(
        background_tasks: BackgroundTasks,
        db: Session = Depends(get_db),
):
    crud.soft_delete_all_dns_records(db)
    background_tasks.add_task(write_dns_to_file, db)
    return {'deleted': True}
