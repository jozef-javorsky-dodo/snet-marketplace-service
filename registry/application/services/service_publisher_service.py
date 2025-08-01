import os
import json
import tempfile
from datetime import datetime as dt
from typing import Any, Dict, Union
from urllib.request import urlretrieve
from uuid import uuid4

from deepdiff import DeepDiff
from cerberus import Validator

from common import utils
from common.boto_utils import BotoUtils
from common.blockchain_util import BlockChainUtil
from common.constant import StatusCode
from common.logger import get_logger

from common.utils import send_email_notification 
from registry.settings import settings

from registry.constants import (
    EnvironmentType,
    ServiceAvailabilityStatus,
    ServiceStatus,
    ServiceSupportType,
    UserType,
    MPE_ADDR_PATH,
)

from registry.application.schemas.service import (
    CreateServiceRequest,
    GetDaemonConfigRequest,
    GetServicesForOrganizationRequest,
    PublishServiceRequest,
    SaveServiceGroupsRequest,
    SaveServiceRequest,
    ServiceDeploymentStatusRequest,
    VerifyServiceIdRequest,
    SaveTransactionHashRequest,
    GetCodeBuildStatusRequest
)
from registry.domain.factory.service_factory import ServiceFactory
from registry.domain.models.demo_component import DemoComponent
from registry.domain.models.offchain_service_config import OffchainServiceConfig
from registry.domain.models.service import Service
from registry.domain.models.organization import Organization
from registry.domain.models.service_comment import ServiceComment
from registry.exceptions import (
    BadRequestException,
    EnvironmentNotFoundException,
    InvalidServiceStateException,
    OrganizationNotFoundException,
    ServiceNotFoundException,
    ServiceProtoNotFoundException,
    InvalidMetadataException
)

from registry.infrastructure.repositories.organization_repository import OrganizationPublisherRepository
from registry.infrastructure.repositories.service_publisher_repository import ServicePublisherRepository
from registry.infrastructure.storage_provider import (
    StorageProvider,
    StorageProviderType,
    FileUtils
)

ALLOWED_ATTRIBUTES_FOR_SERVICE_SEARCH = ["display_name"]
DEFAULT_ATTRIBUTE_FOR_SERVICE_SEARCH = "display_name"
ALLOWED_ATTRIBUTES_FOR_SERVICE_SORT_BY = ["ranking", "service_id"]
DEFAULT_ATTRIBUTES_FOR_SERVICE_SORT_BY = "ranking"
ALLOWED_ATTRIBUTES_FOR_SERVICE_ORDER_BY = ["asc", "desc"]
DEFAULT_ATTRIBUTES_FOR_SERVICE_ORDER_BY = "desc"
NETWORK_ID = settings.network.id
DEFAULT_OFFSET = 0
DEFAULT_LIMIT = 0
BUILD_FAILURE_CODE = 0

logger = get_logger(__name__)
service_factory = ServiceFactory()
boto_util = BotoUtils(region_name=settings.aws.REGION_NAME)
validator = Validator()


class ServicePublisherService:
    def __init__(self, lighthouse_token: Union[str, None] = None):
        self._storage_provider = StorageProvider(lighthouse_token)

    def service_build_status_notifier(self, username: str, request: ServiceDeploymentStatusRequest):
        if request.build_status == BUILD_FAILURE_CODE:
            BUILD_FAIL_MESSAGE = "Build failed please check your components"
            service = ServicePublisherRepository().get_service_for_given_service_id_and_org_id(
                request.org_id, request.service_id
            )

            if service is None:
                raise Exception()

            contacts = [contributor.get("email_id", "") for contributor in service.contributors]

            service_comment = ServiceComment(
                service.org_uuid,
                service.uuid,
                "SERVICE_APPROVAL",
                "SERVICE_APPROVER",
                username,
                BUILD_FAIL_MESSAGE
            )

            ServicePublisherRepository().save_service_comments(service_comment)
            ServicePublisherRepository().save_service(username, service, ServiceStatus.CHANGE_REQUESTED.value)

            try:
                BUILD_STATUS_SUBJECT = "Build failed for your service {}"
                BUILD_STATUS_MESSAGE = "Build failed for your org_id {} and service_id {}"
                send_email_notification(
                    contacts, BUILD_STATUS_SUBJECT.format(request.service_id),
                    BUILD_STATUS_MESSAGE.format(request.org_id, request.service_id),
                    settings.lambda_arn.NOTIFICATION_ARN,
                    boto_util
                )
            except Exception:
                logger.info(f"Error happened while sending build_status mail for {request.org_id} and contacts {contacts}")

    def get_service_id_availability_status(self, request: VerifyServiceIdRequest):
        record_exist = ServicePublisherRepository().check_service_id_within_organization(
            request.org_uuid, request.service_id
        )
        if record_exist:
            return ServiceAvailabilityStatus.UNAVAILABLE.value
        return ServiceAvailabilityStatus.AVAILABLE.value

    @staticmethod
    def get_service_for_org_id_and_service_id(org_id, service_id):
        service = ServicePublisherRepository().get_service_for_given_service_id_and_org_id(org_id, service_id)
        if not service:
            return {}
        return service.to_dict()

    @staticmethod
    def _get_valid_service_contributors(contributors):
        for contributor in contributors:
            email_id = contributor.get("email_id", None)
            name = contributor.get("name", None)
            if (email_id is None or len(email_id) == 0) and (name is None or len(name) == 0):
                contributors.remove(contributor)
        return contributors

    def _save_service_comment(
        self,
        org_uuid: str,
        service_uuid: str,
        username: str,
        support_type: str,
        user_type: str,
        comment: str
    ):
        service_provider_comment = ServiceFactory.create_service_comment_entity_model(
            org_uuid=org_uuid,
            service_uuid=service_uuid,
            support_type=support_type,
            user_type=user_type,
            commented_by=username,
            comment=comment
        )
        ServicePublisherRepository().save_service_comments(service_provider_comment)

    def save_offline_service_configs(self, request: SaveServiceRequest):
        demo_component_required = request.assets.get("demo_files", {}).get("required", -1)
        
        if demo_component_required == -1:
            return

        offchain_service_config = OffchainServiceConfig(
            org_uuid=request.org_uuid,
            service_uuid=request.service_uuid,
            configs={
                "demo_component_required": str(demo_component_required)
            }
        )
        ServicePublisherRepository().add_or_update_offline_service_config(offchain_service_config)

    def save_service(self, username: str, request: SaveServiceRequest):
        service = ServicePublisherRepository().get_service_for_given_service_uuid(
            request.org_uuid, request.service_uuid
        )
        
        if service is None:
            raise Exception()
        
        service.service_id = request.service_id
        service.proto = request.proto
        service.storage_provider = request.storage_provider
        service.display_name = request.display_name
        service.short_description = request.short_description
        service.description = request.description
        service.project_url = request.project_url
        service.service_type = request.service_type
        service.service_state.transaction_hash = request.transaction_hash
        service.tags = request.tags
        service.mpe_address = request.mpe_address

        service.contributors = ServicePublisherService._get_valid_service_contributors(
            contributors=request.contributors
        )

        groups = []
        for group in request.groups:
            service_group = ServiceFactory.create_service_group_entity_model(
                request.org_uuid, request.service_uuid, group
            )
            logger.info(f"group service_uuid: {service_group.service_uuid}")
            groups.append(service_group)
        logger.info(f"New Service Groups: {groups}")
        service.groups = groups
        
        ServicePublisherRepository().save_service(username, service, ServiceStatus.APPROVED.value)
        
        comment = request.comments.get(UserType.SERVICE_PROVIDER.value, "")
        if len(comment) > 0:
            self._save_service_comment(
                org_uuid=request.org_uuid,
                service_uuid=request.service_uuid,
                support_type="SERVICE_APPROVAL",
                user_type="SERVICE_PROVIDER",
                username=username,
                comment=comment
            )
        
        self.save_offline_service_configs(request)
        
        service = self.get_service_for_given_service_uuid(request.org_uuid, request.service_uuid)
        
        return service

    def save_service_groups(self, username: str, request: SaveServiceGroupsRequest):
        service_db = ServicePublisherRepository().get_service_for_given_service_uuid(
            request.org_uuid, request.service_uuid
        )
        service = ServiceFactory.convert_service_db_model_to_entity_model(service_db)

        if service is None:
            raise Exception()

        service.groups = [
            ServiceFactory.create_service_group_entity_model(
                request.org_uuid, request.service_uuid, group
            ) for group in request.groups
        ]

        saved_service = ServicePublisherRepository().save_service(
            username, service, service.service_state.state
        )

        return saved_service.to_dict()

    def save_transaction_hash_for_published_service(
        self,
        username: str,
        request: SaveTransactionHashRequest
    ):
        service = ServicePublisherRepository().get_service_for_given_service_uuid(
            request.org_uuid, request.service_uuid
        )
        
        if service is None:
            raise BadRequestException()
        
        if service.service_state.state == ServiceStatus.APPROVED.value:
            service.service_state = ServiceFactory().create_service_state_entity_model(
                request.org_uuid,
                request.service_uuid,
                ServiceStatus.PUBLISH_IN_PROGRESS.value,
                request.transaction_hash
            )
            ServicePublisherRepository().save_service(
                username, service, ServiceStatus.PUBLISH_IN_PROGRESS.value
            )

        return StatusCode.OK

    def create_service(self, username: str, request: CreateServiceRequest):
        service_uuid = uuid4().hex
        service = ServiceFactory.create_service_entity_model_from_request(
            request, service_uuid, ServiceStatus.DRAFT.value
        )

        ServicePublisherRepository().add_service(service, username)

        return {"org_uuid": request.org_uuid, "service_uuid": service_uuid}

    def get_services_for_organization(self, request: GetServicesForOrganizationRequest):
        filter_parameters = {
            "offset": request.offset,
            "limit": request.limit,
            "search_string": request.search_string,
            "search_attribute": request.search_attribute if request.search_attribute in ALLOWED_ATTRIBUTES_FOR_SERVICE_SEARCH else DEFAULT_ATTRIBUTE_FOR_SERVICE_SEARCH,
            "sort_by": request.sort_by if request.sort_by in ALLOWED_ATTRIBUTES_FOR_SERVICE_SORT_BY else DEFAULT_ATTRIBUTES_FOR_SERVICE_SORT_BY,
            "order_by": request.order_by if request.order_by in ALLOWED_ATTRIBUTES_FOR_SERVICE_SORT_BY else DEFAULT_ATTRIBUTES_FOR_SERVICE_ORDER_BY
        }

        services = ServicePublisherRepository().get_services_for_organization(
            request.org_uuid, filter_parameters
        )

        search_result = [service.to_dict() for service in services]
        search_count = ServicePublisherRepository().get_total_count_of_services_for_organization(
            request.org_uuid, filter_parameters
        )

        return {"total_count": search_count, "offset": request.offset, "limit": request.limit, "result": search_result}

    def get_service_comments(self, org_uuid: str, service_uuid: str):
        service_provider_comment = ServicePublisherRepository().get_last_service_comment(
            org_uuid=org_uuid,
            service_uuid=service_uuid,
            support_type=ServiceSupportType.SERVICE_APPROVAL.value,
            user_type=UserType.SERVICE_PROVIDER.value
        )

        approver_comment = ServicePublisherRepository().get_last_service_comment(
            org_uuid=org_uuid,
            service_uuid=service_uuid,
            support_type=ServiceSupportType.SERVICE_APPROVAL.value,
            user_type=UserType.SERVICE_APPROVER.value
        )

        return {
            UserType.SERVICE_PROVIDER.value: None if not service_provider_comment else f"{service_provider_comment.comment}",
            UserType.SERVICE_APPROVER.value: "<div></div>" if not approver_comment else f"<div>{approver_comment.comment}</div>"
        }

    def map_offchain_service_config(self, offchain_service_config, service):
        # update demo component flag in service assets
        if "demo_files" not in service["media"]:
            service["media"]["demo_files"] = {}
        service["media"]["demo_files"].update({"required": offchain_service_config.configs["demo_component_required"]})
        return service

    def get_service_for_given_service_uuid(self, org_uuid: str, service_uuid: str):
        service = ServicePublisherRepository().get_service_for_given_service_uuid(
            org_uuid, service_uuid
        )
        if not service:
            return None

        service.comments = self.get_service_comments(org_uuid, service_uuid)
        offchain_service_config = ServicePublisherRepository().get_offchain_service_config(
            org_uuid=org_uuid,
            service_uuid=service_uuid
        )

        service_data = service.to_dict()
        if offchain_service_config.configs:
            service_data = self.map_offchain_service_config(offchain_service_config, service_data)

        return service_data

    def publish_assets(self, service: Service, storage_provider_enum: StorageProviderType):
        """
        Publishes supported service assets to the specified storage provider.

        :param service: Service object containing assets.
        :param storage_provider_enum: Enum value for the storage provider.
        """
        ASSETS_SUPPORTED = ["hero_image", "demo_files"]
        supported_assets = {k: v for k, v in service.assets.items() if k in ASSETS_SUPPORTED}

        for asset_name, asset_data in supported_assets.items():
            try:
                asset_url = asset_data.get("url")
                if not asset_url:
                    logger.warning(f"Asset URL for '{asset_name}' is missing. Skipping...")
                    continue

                logger.info(f"Downloading asset '{asset_name}' from: {asset_url}")

                source_path = self._download_file(asset_url)
                logger.info(f"Downloaded asset '{asset_name}' to: {source_path}")

                asset_hash = self._storage_provider.publish(source_path, storage_provider_enum)
                logger.info(f"Published asset '{asset_name}'. Hash: {asset_hash}")

                service.assets[asset_name]["hash"] = asset_hash

            except Exception as e:
                logger.error(f"Failed to process asset '{asset_name}': {str(e)}")

    def publish_service_data_to_storage_provider(
        self,
        username: str,
        request: PublishServiceRequest,
    ) -> Service:
        """
        Publishes the service's assets and protos to storage provider and updates the service's metadata.

        :param storage_provider_enum: Enum value for the storage provider (e.g., IPFS, Filecoin).
        :return: Updated Service object.
        :raises ServiceProtoNotFoundException: If the proto files are not found in the service assets.
        :raises InvalidServiceStateException: If the service is not in the APPROVED state.
        """
        service = self._get_approved_service(request.org_uuid, request.service_uuid)

        proto_url = service.assets.get("proto_files", {}).get("url")
        if not proto_url:
            raise ServiceProtoNotFoundException()

        proto_file_path = self._download_file(proto_url)
        logger.info(f"Proto file downloaded to: {proto_file_path}")

        asset_hash = self._storage_provider.publish(proto_file_path, request.storage_provider, zip_archive=True)
        logger.info(f"Published proto files. Hash: {asset_hash}")

        return self._update_service_metadata(username, service, asset_hash, request.storage_provider)

    def _get_approved_service(self, org_uuid: str, service_uuid: str) -> Service:
        """
        Fetches the service from the repository and validates its state.

        :return: Service object if it is in the APPROVED state.
        :raises InvalidServiceStateException: If the service is not in the APPROVED state.
        """
        service_repo = ServicePublisherRepository()
        service = service_repo.get_service_for_given_service_uuid(org_uuid, service_uuid)

        if service is None:
            raise BadRequestException()

        if service.service_state.state != ServiceStatus.APPROVED.value:
            logger.error(f"Service status must be {ServiceStatus.APPROVED.value} to publish.")
            raise InvalidServiceStateException()
        return service

    def _download_file(self, url: str) -> str:
        """
        Downloads a file from the given URL to a temporary location.

        :param url: URL of the file.
        :return: Path to the downloaded temporary file.
        """
        try:
            # Create a temporary file with a proper suffix based on the URL's file extension
            file_suffix = os.path.splitext(url)[-1]  # Extract the file extension from the URL
            with tempfile.NamedTemporaryFile(delete=False, suffix=file_suffix) as temp_file:
                temp_file_path = temp_file.name

            # Download the file to the temporary file location
            urlretrieve(url, temp_file_path)  # Replace this with your download function if needed
            logger.info(f"File downloaded to temporary location: {temp_file_path}")
            return temp_file_path

        except Exception as e:
            logger.error(f"Failed to download file from URL '{url}': {str(e)}")
            raise

    def _update_service_metadata(
        self,
        username: str,
        service: Service,
        asset_hash: str,
        storage_provider_enum: StorageProviderType,    
    ) -> Service:
        """
        Updates the service metadata and persists it in the repository.

        :param service: Service object to update.
        :param asset_hash: Hash of the published proto file.
        :param storage_provider_enum: Enum value for the storage provider.
        """
        service.proto = {
            "model_hash": asset_hash,
            "encoding": "proto",
            "service_type": service.service_type,
        }
        service.assets["proto_files"]["hash"] = asset_hash
        self.publish_assets(service, storage_provider_enum)

        service_repo = ServicePublisherRepository()
        return service_repo.save_service(username, service, service.service_state.state)

    @staticmethod
    def notify_service_contributor_when_user_submit_for_approval(org_id, service_id, contributors):
        # notify service contributor for submission via email
        recipients = [contributor.get("email_id", "") for contributor in contributors]
        if not recipients:
            logger.info(f"Unable to find service contributors for service {service_id} under {org_id}")
            return
        notification_subject = f"Your service {service_id} has successfully submitted for approval"
        notification_message = f"Your service {service_id} under organization {org_id} has successfully been submitted " \
                               f"for approval. We will notify you once it is reviewed by our approval team. It usually " \
                               f"takes around five to ten business days for approval."
        utils.send_email_notification(
            recipients,
            notification_subject,
            notification_message,
            settings.lambda_arn.NOTIFICATION_ARN,
            boto_util
        )

    def daemon_config(self, request: GetDaemonConfigRequest):
        organization = OrganizationPublisherRepository().get_organization(
            org_uuid=request.org_uuid
        )
        if not organization:
            raise OrganizationNotFoundException()

        service = ServicePublisherRepository().get_service_for_given_service_uuid(
            request.org_uuid, request.service_uuid
        )
        if not service:
            raise ServiceNotFoundException()
    
        organization_members = OrganizationPublisherRepository().get_org_member(org_uuid=request.org_uuid)

        network_name = settings.network.networks[NETWORK_ID].name
        network_name = "main" if network_name == "mainnet" else network_name

        if request.network is EnvironmentType.MAIN:
            daemon_config = {
                "ipfs_end_point": f"{settings.ipfs.URL}:{settings.ipfs.PORT}",
                "blockchain_network_selected": network_name,
                "organization_id": organization.id,
                "service_id": service.service_id,
                "metering_end_point": f"https://{network_name}-marketplace.singularitynet.io",
                "authentication_addresses": [member.address for member in organization_members],
                "blockchain_enabled": True,
                "passthrough_enabled": True
            }
        else:
            raise EnvironmentNotFoundException()
        return daemon_config

    def get_service_demo_component_build_status(self, request: GetCodeBuildStatusRequest):
        build_id: str | None = None
        try:
            service = self.get_service_for_given_service_uuid(request.org_uuid, request.service_uuid)
            if service:
                build_id = service["media"]["demo_files"]["build_id"]
                build_response = boto_util.get_code_build_details(build_ids=[build_id])
                build_data = [data for data in build_response['builds'] if data['id'] == build_id]
                status = build_data[0]['buildStatus']
            else:
                raise Exception(f"service for org {request.org_uuid} and service {service} is not found")
            return {"build_status": status}
        except Exception as e:
            logger.info(
                f"error in triggering build_id {build_id} for service {request.service_uuid} and org {request.org_uuid} :: error {repr(e)}"
            )
            raise e

    def get_existing_offchain_configs(self, existing_service_data):
        existing_offchain_configs = {}
        if "demo_component" in existing_service_data:
            existing_offchain_configs.update(
                {"demo_component": existing_service_data["demo_component"]})
        return existing_offchain_configs

    def are_blockchain_attributes_got_updated(self, existing_metadata, current_service_metadata):
        change = DeepDiff(current_service_metadata, existing_metadata)
        logger.info(f"Change in blockchain attributes::{change}")
        return True if change else False

    def get_offchain_changes(self, current_offchain_config, existing_offchain_config, current_service):
        changes = {}
        existing_demo = existing_offchain_config.get("demo_component", {})
        new_demo = DemoComponent(
            demo_component_required=current_offchain_config["demo_component_required"],
            demo_component_url=current_service.assets.get("demo_files", {}).get("url", ""),
            demo_component_status=current_service.assets.get("demo_files", {}).get("status", "")
        )
        demo_changes = new_demo.to_dict()
        demo_last_modified = existing_demo.get("demo_component_last_modified", "")
        # if last_modified not there publish if it there and is greater than current last modifed publish
        demo_changes.update({"change_in_demo_component": 1})
        current_demo_last_modified = current_service.assets.get("demo_files", {}).get("last_modified")
        if demo_last_modified and \
            (current_demo_last_modified is None or
             dt.fromisoformat(demo_last_modified) > dt.fromisoformat(current_demo_last_modified)):
            demo_changes.update({"change_in_demo_component": 0})
        changes.update({"demo_component": demo_changes})
        return changes

    def publish_offchain_service_configs(self, org_id, service_id, payload, token_name):
        publish_offchain_attributes_arn = settings.lambda_arn.PUBLISH_OFFCHAIN_ATTRIBUTES_ARN[token_name]
        logger.info(f"publish attributes arn: {publish_offchain_attributes_arn}")
        payload = {
            "pathParameters": {
                "org_id": org_id,
                "service_id": service_id
            },
            "body": json.dumps(payload)
        }
        response = boto_util.invoke_lambda(
            publish_offchain_attributes_arn,
            "RequestResponse",
            json.dumps(payload)
        )

        logger.info(f"Publish attributes response: {response}")
        response = json.loads(response.get("body"))
        logger.info(f"Get service response body: {response}")

        if response["status"] != "success":
            raise Exception(f"Error in publishing offchain service attributes for org_id :: {org_id} service_id :: {service_id}")


    def get_existing_service_details_from_contract_api(self, service_id, org_id, token_name):
        get_service_arn = settings.lambda_arn.GET_SERVICE_FOR_GIVEN_ORG_LAMBDAS[token_name]
        logger.info(f"get service arn: {get_service_arn}")
        payload = {
            "pathParameters": {
                "orgId": org_id,
                "serviceId": service_id
            }
        }
        response = boto_util.invoke_lambda(
            get_service_arn,
            "RequestResponse",
            json.dumps(payload)
        )

        logger.info(f"Get service response: {response}")
        response = json.loads(response.get("body"))
        logger.info(f"Get service response body: {response}")

        if response["status"] != "success":
            raise Exception(f"Error getting service details for org_id :: {org_id} service_id :: {service_id}")
        logger.debug(f"Get service by org_id from contract_api :: {response}")

        return response["data"]

    def publish_new_offchain_configs(
        self,
        username: str,
        current_service: Service,
        request: PublishServiceRequest
    ) -> Dict[str, Union[bool, str]]:
        organization = OrganizationPublisherRepository().get_organization(org_uuid=request.org_uuid)
        if organization is None:
            raise BadRequestException()

        logger.debug(f"Current organization :: {organization.to_response()}")

        service_mpe_address = current_service.mpe_address
        token_name = self.__get_token_name(service_mpe_address)

        existing_service_data = self.get_existing_service_details_from_contract_api(
            current_service.service_id, organization.id, token_name
        )
        logger.debug(f"Existing service data :: {existing_service_data}")

        existing_metadata = (
            self._storage_provider.get(existing_service_data["hash_uri"])
            if existing_service_data else {}
        )
        publish_to_blockchain = self.are_blockchain_attributes_got_updated(
            existing_metadata, current_service.to_metadata()
        )
        logger.debug(f"Publish to blockchain :: {publish_to_blockchain}")

        existing_offchain_configs = self.get_existing_offchain_configs(existing_service_data)
        current_offchain_configs = ServicePublisherRepository().get_offchain_service_config(
            org_uuid=request.org_uuid, service_uuid=request.service_uuid
        )

        logger.debug(f"Current offchain configs :: {current_offchain_configs}")
        logger.debug(f"Existing offchain configs :: {existing_offchain_configs}")

        new_offchain_configs = self.get_offchain_changes(
            current_offchain_config=current_offchain_configs.configs,
            existing_offchain_config=existing_offchain_configs,
            current_service=current_service
        )
        logger.debug(f"New offchain configs :: {new_offchain_configs}")

        status = self._prepare_publish_status(
            username,
            organization,
            current_service,
            request.storage_provider,
            publish_to_blockchain,
            new_offchain_configs,
            token_name,
        )
        logger.debug(f"Prepare publish status result :: {status}")

        return status

    def _prepare_publish_status(
        self,
        username: str,
        organization: Organization,
        current_service: Service,
        storage_provider: StorageProviderType,
        publish_to_blockchain: bool,
        new_offchain_configs: Dict[str, Any],
        token_name: str
    ):
        status: Dict[str, str | bool] = {"publish_to_blockchain": publish_to_blockchain}

        if publish_to_blockchain:
            filepath = FileUtils.create_temp_json_file(current_service.to_metadata())
            # filename = f"{METADATA_FILE_PATH}/{current_service.uuid}_service_metadata.json"
            status["service_metadata_uri"] = self._storage_provider.publish(filepath, storage_provider)
            current_service.metadata_uri = status["service_metadata_uri"]

        logger.info("Publish offchain service configs to contract_api")
        self.publish_offchain_service_configs(
            org_id=organization.id,
            service_id=current_service.service_id,
            payload=new_offchain_configs,
            token_name=token_name
        )

        if not publish_to_blockchain:
            ServicePublisherRepository().save_service(
                username=username,
                service=current_service,
                state=ServiceStatus.PUBLISHED.value
            )

        return status

    def publish_service(self, username: str, request: PublishServiceRequest):
        current_service = self.publish_service_data_to_storage_provider(username, request)
        logger.debug(f"Current service :: {current_service.to_dict()}")

        if not Service.is_metadata_valid(service_metadata=current_service.to_metadata()):
            raise InvalidMetadataException()

        return self.publish_new_offchain_configs(username, current_service, request)

    @staticmethod
    def __get_token_name(mpe_address) -> str:
        mpe_contract = BlockChainUtil.load_contract(MPE_ADDR_PATH)
        network_data = mpe_contract[str(NETWORK_ID)]
        for token, data in network_data.items():
            if data[settings.stage]["address"] == mpe_address:
                return token
        raise Exception(f"Unable to find token name for mpe address {mpe_address}")
