import logging
from typing import List, Optional, TypeVar
import itertools

import httpx
import asyncio

from app.schemas import BaseDNSRecord, Types, DNSRecordCloudflare, DNSRecordDB
from app.config import settings

logger = logging.getLogger(__name__)

BASE_URL = 'https://api.cloudflare.com/client/v4/'


class DomainAuth(httpx.Auth):
    def __init__(self, domain):
        self.domain = domain

    def auth_flow(self, request):
        token = settings.domain_config[self.domain].jwt
        request.headers['Authorization'] = f'Bearer {token}'
        yield request


T = TypeVar('T', bound=BaseDNSRecord)


def lookup_in_list_of_dns_records(name: str, dns_records: List[T]) -> Optional[T]:
    return next(
        (dns_record for dns_record in dns_records if dns_record.name == name), None
    )


async def get_all_dns_records_cf(client: httpx.AsyncClient):
    _dns_records_cf = []

    for domain, config in settings.domain_config.items():
        for page in itertools.count(start=1):
            per_page = 100
            r = await client.get(
                f"zones/{config.zone_id}/dns_records",
                params={'page': page, 'per_page': per_page},
                auth=DomainAuth(domain),
            )
            page_dns_records = r.json()['result']
            _dns_records_cf.extend(page_dns_records)

            if len(page_dns_records) < per_page:
                break

    return [
        DNSRecordCloudflare(**dns_record)
        for dns_record in _dns_records_cf
        if dns_record['type'] in Types.__members__.values()
    ]


async def sync_dns_record(
    dns_record_db: DNSRecordDB,
    dns_record_cf: DNSRecordCloudflare,
    client: httpx.AsyncClient,
):
    response_futures = []

    if dns_record_db.to_delete and dns_record_cf is None:
        logger.warning(
            f'DNS Record in DB is marked for deletion but does not exist (record: {dns_record_db})'
        )
    elif dns_record_db.to_delete:
        if BaseDNSRecord(**dns_record_db.dict()) != BaseDNSRecord(
            **dns_record_cf.dict()
        ):
            logger.warning(
                'DNS record in cloudflare does not match DNS record to be deleted, '
                'it might have been manually changed'
            )
        logger.info(f'Delete: {dns_record_cf}')
        response_futures.append(
            client.delete(
                f"zones/{dns_record_cf.zone_id}/dns_records/{dns_record_cf.id}",
                auth=DomainAuth(dns_record_cf.domain),
            )
        )
    elif dns_record_cf is None:
        # create
        logger.info(f'Create: {dns_record_db}')
        dns_record_cf_upload = BaseDNSRecord(**dns_record_db.dict())
        response_futures.append(
            client.post(
                f'zones/{dns_record_cf_upload.zone_id}/dns_records',
                json=dns_record_cf_upload.dict(),
                auth=DomainAuth(dns_record_db.domain),
            )
        )
    elif BaseDNSRecord(**dns_record_db.dict()) == BaseDNSRecord(**dns_record_cf.dict()):
        # already matches exactly, skip
        logger.debug(f'Name: "{dns_record_db.name}" is up to date')
    elif BaseDNSRecord(**dns_record_db.dict()) != BaseDNSRecord(**dns_record_cf.dict()):
        # name already exists but record doesn't match, update
        logger.info(f'Update: {dns_record_db}')
        dns_record_cf_upload = BaseDNSRecord(**dns_record_db.dict())
        response_futures.append(
            client.put(
                f'zones/{dns_record_cf_upload.zone_id}/dns_records/{dns_record_cf.id}',
                json=dns_record_cf_upload.dict(),
                auth=DomainAuth(dns_record_db.domain),
            )
        )

    for response_future in asyncio.as_completed(response_futures):
        try:
            response = await response_future
            response.raise_for_status()
        except httpx.RequestError as exc:
            logger.info(
                f"An error occurred while requesting {exc.request.method!r} {exc.request.url!r}."
            )
        except httpx.HTTPStatusError as exc:
            logger.warning(
                f"Error response {exc.response.status_code}: {exc.response.read()},"
                f" while doing {exc.request.method!r} {exc.request.url!r} with: {exc.request.read()!r}"
            )


async def sync_dns_records(
    dns_records_db: List[DNSRecordDB], client: httpx.AsyncClient
):
    dns_records_cf = await get_all_dns_records_cf(client)

    for i in dns_records_cf:
        logger.debug(i)

    for dns_record_db in dns_records_db:
        dns_record_cf = lookup_in_list_of_dns_records(
            dns_record_db.name, dns_records_cf
        )

        await sync_dns_record(dns_record_db, dns_record_cf, client=client)
