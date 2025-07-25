from web3 import Web3

from common.logger import get_logger
from contract_api.application.consumers.event_consumer import EventConsumer
from contract_api.application.schemas.consumer_schemas import RegistryEventConsumerRequest
from contract_api.domain.models.org_group import NewOrgGroupDomain
from contract_api.domain.models.organization import NewOrganizationDomain
from contract_api.infrastructure.db import DefaultSessionFactory, session_scope
from contract_api.infrastructure.repositories.new_organization_repository import (
    NewOrganizationRepository,
)

from sqlalchemy.orm import Session


logger = get_logger(__name__)


class OrganizationCreatedEventConsumer(EventConsumer):
    def __init__(self):
        super().__init__()
        self._organization_repository = NewOrganizationRepository()
        self._session_factory = DefaultSessionFactory

    def on_event(
        self, request: RegistryEventConsumerRequest | None = None, org_id: str | None = None
    ):
        if org_id is None:
            org_id = request.org_id
        org_id, blockchain_org_data, org_metadata, org_metadata_uri = (
            self._get_org_details_from_blockchain(org_id)
        )

        self._process_organization_create_update_event(
            org_id, blockchain_org_data, org_metadata, org_metadata_uri
        )

    def _process_organization_create_update_event(
        self, org_id, org_data, org_metadata, org_metadata_uri
    ):
        if org_data is not None and org_data[0]:
            with session_scope(self._session_factory) as session:
                new_assets_hash = org_metadata.get("assets", {})
                new_assets_url_mapping = self._get_new_assets_url(session, org_id, org_metadata)
                description = org_metadata.get("description", "")
                contacts = org_metadata.get("contacts", {})

                self._organization_repository.upsert_organization(
                    session,
                    NewOrganizationDomain(
                        org_id=org_id,
                        organization_name=org_metadata["org_name"],
                        owner_address=org_data[3],
                        org_metadata_uri=org_metadata_uri,
                        org_assets_url=new_assets_url_mapping,
                        is_curated=True,
                        description=description,
                        assets_hash=new_assets_hash,
                        contacts=contacts,
                    ),
                )
                self._organization_repository.delete_org_groups(session=session, org_id=org_id)
                new_groups = [
                    NewOrgGroupDomain(
                        org_id=org_id,
                        group_id=group["group_id"],
                        group_name=group["group_name"],
                        payment=group["payment"],
                    )
                    for group in org_metadata.get("groups", [])
                ]
                self._organization_repository.create_org_groups(session=session, groups=new_groups)

    def _get_new_assets_url(self, session: Session, org_id: str, new_ipfs_data: dict):
        new_assets_hash = new_ipfs_data.get("assets", {})
        logger.info(f"New_assets_hash: {new_assets_hash}")
        existing_assets_hash = {}
        existing_assets_url = {}

        existing_organization = self._organization_repository.get_organization(session, org_id)
        if existing_organization is not None:
            existing_assets_hash = existing_organization.assets_hash
            existing_assets_url = existing_organization.org_assets_url
        new_assets_url_mapping = self._compare_assets_and_push_to_s3(
            existing_assets_hash, new_assets_hash, existing_assets_url, org_id, ""
        )
        return new_assets_url_mapping

    def _get_org_details_from_blockchain(self, org_id):
        registry_contract = self._get_contract("REGISTRY")

        logger.info(f"Organization id: {org_id}")
        encoded_org_id = Web3.to_bytes(text=org_id).ljust(32, b"\0")[:32]
        logger.info(f"Encoded organization id: {encoded_org_id}")
        blockchain_org_data = registry_contract.functions.getOrganizationById(encoded_org_id).call()

        org_metadata_uri = Web3.to_text(blockchain_org_data[2]).rstrip("\x00")
        logger.info(f"Organization metadata uri hash: {org_metadata_uri}")

        org_metadata = self._storage_provider.get(org_metadata_uri)

        return org_id, blockchain_org_data, org_metadata, org_metadata_uri


class OrganizationDeletedEventConsumer(EventConsumer):
    def __init__(self):
        super().__init__()
        self._organization_repository = NewOrganizationRepository()

    def on_event(self, request: RegistryEventConsumerRequest, org_id=None):
        if org_id is None:
            org_id = request.org_id
        with session_scope(DefaultSessionFactory) as session:
            self._organization_repository.delete_organization(session, org_id)
