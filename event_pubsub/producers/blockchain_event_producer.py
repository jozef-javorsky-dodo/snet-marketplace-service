import os

from common.blockchain_util import BlockChainUtil, ContractType
from common.logger import get_logger
from event_pubsub.config import CONTRACT_BASE_PATH, READ_EVENTS_WITH_BLOCK_DIFFERENCE, TOKEN_NAME, STAGE
from event_pubsub.event_repository import EventRepository
from event_pubsub.producers.event_producer import EventProducer
from event_pubsub.constants import EventType, NodeModulesPackagePath

logger = get_logger(__name__)


class BlockchainEventProducer(EventProducer):
    def __init__(self, http_provider, contract_name, repository=None):
        self._blockchain_util = BlockChainUtil("HTTP_PROVIDER", http_provider)
        self._event_repository = EventRepository(repository)
        self._contract_name = contract_name

    @staticmethod
    def _get_base_contract_path():
        return os.path.abspath(os.path.join(f"{CONTRACT_BASE_PATH}/node_modules/singularitynet-platform-contracts"))

    def _get_events_from_blockchain(self, start_block_number, end_block_number, net_id):

        base_contract_path = self._get_base_contract_path()
        contract = self._blockchain_util.get_contract_instance(base_contract_path, self._contract_name,
                                                               net_id=net_id, token_name=TOKEN_NAME,
                                                               stage=STAGE)
        contract_events = contract.events
        all_blockchain_events = []

        for attributes in contract_events.abi:
            if attributes['type'] == 'event':
                event_name = attributes['name']
                event_object = getattr(contract.events, event_name)
                blockchain_events = event_object.createFilter(fromBlock=start_block_number,
                                                              toBlock=end_block_number).get_all_entries()
                all_blockchain_events.extend(blockchain_events)

        return all_blockchain_events

    def _produce_contract_events(self, start_block_number, end_block_number, net_id):

        events = self._get_events_from_blockchain(start_block_number, end_block_number, net_id)
        logger.info(f"read no of events {len(events)}")
        return events

    def _get_end_block_number(self, last_processed_block_number, batch_limit):
        current_block_number = self._blockchain_util.get_current_block_no()
        logger.info(f"Current block number={current_block_number}")

        if READ_EVENTS_WITH_BLOCK_DIFFERENCE:
            block_number_with_difference = current_block_number - READ_EVENTS_WITH_BLOCK_DIFFERENCE
        else:
            block_number_with_difference = current_block_number

        end_block_number = last_processed_block_number + batch_limit
        if block_number_with_difference <= end_block_number:
            end_block_number = block_number_with_difference

        return end_block_number

    def produce_event(self, net_id):
        pass


class RegistryEventProducer(BlockchainEventProducer):
    REGISTRY_EVENT_READ_BATCH_LIMIT = 50000

    def __init__(self, http_provider, repository=None):
        super().__init__(http_provider, "REGISTRY", repository)

    def _push_event(self, event):
        """
          `row_id` int(11) NOT NULL AUTO_INCREMENT,
          `block_no` int(11) NOT NULL,
          `event` varchar(256) NOT NULL,
          `json_str` text,
          `processed` bit(1) DEFAULT NULL,
          `transactionHash` varchar(256) DEFAULT NULL,
          `logIndex` varchar(256) DEFAULT NULL,
          `error_code` int(11) DEFAULT NULL,
          `error_msg` varchar(256) DEFAULT NULL,
          `row_updated` timestamp NULL DEFAULT NULL,
          `row_created` timestamp NULL DEFAULT NULL,
        :param event:
        :return:
        """

        block_number = event.blockNumber
        event_name = event.event
        json_str = str(dict(event.args))
        processed = 0
        transaction_hash = event.transactionHash.hex()
        log_index = event.logIndex
        error_code = 0
        error_message = ""
        event_type = EventType.REGISTRY.value

        self._event_repository.insert_raw_event(event_type, block_number, event_name, json_str, processed,
                                                transaction_hash, log_index, error_code, error_message)

    def _push_events_to_repository(self, events):
        for event in events:
            self._push_event(event)

    def produce_event(self, net_id):
        last_block_number = self._event_repository.read_last_read_block_number_for_event(self._contract_name)
        end_block_number = self._get_end_block_number(last_block_number,
                                                      RegistryEventProducer.REGISTRY_EVENT_READ_BATCH_LIMIT)
        logger.info(f"reading registry event from {last_block_number} to {end_block_number}")
        events = self._produce_contract_events(last_block_number, end_block_number, net_id)
        self._push_events_to_repository(events)
        self._event_repository.update_last_read_block_number_for_event(self._contract_name, end_block_number)

        return events


class MPEEventProducer(BlockchainEventProducer):
    MPE_EVENT_READ_BATCH_LIMIT = 50000

    def __init__(self, http_provider, repository=None):
        super().__init__(http_provider, "MPE", repository)

    def _push_event(self, event):
        """
          `row_id` int(11) NOT NULL AUTO_INCREMENT,
          `block_no` int(11) NOT NULL,
          `event` varchar(256) NOT NULL,
          `json_str` text,
          `processed` bit(1) DEFAULT NULL,
          `transactionHash` varchar(256) DEFAULT NULL,
          `logIndex` varchar(256) DEFAULT NULL,
          `error_code` int(11) DEFAULT NULL,
          `error_msg` varchar(256) DEFAULT NULL,
          `row_updated` timestamp NULL DEFAULT NULL,
          `row_created` timestamp NULL DEFAULT NULL,
        :param event:
        :return:
        """

        block_number = event.blockNumber
        event_name = event.event
        json_str = str(dict(event.args))
        processed = 0
        transaction_hash = event.transactionHash.hex()
        log_index = event.logIndex
        error_code = 0
        error_message = ""
        event_type = EventType.MPE.value

        self._event_repository.insert_raw_event(event_type, block_number, event_name, json_str, processed,
                                                transaction_hash, log_index, error_code, error_message)

    def _push_events_to_repository(self, events):
        for event in events:
            self._push_event(event)

    def produce_event(self, net_id):
        last_block_number = self._event_repository.read_last_read_block_number_for_event(self._contract_name)
        end_block_number = self._get_end_block_number(last_block_number, self.MPE_EVENT_READ_BATCH_LIMIT)
        logger.info(f"reading mpe event from {last_block_number} to {end_block_number}")
        events = self._produce_contract_events(last_block_number, end_block_number, net_id)
        self._push_events_to_repository(events)
        self._event_repository.update_last_read_block_number_for_event(self._contract_name, end_block_number)
        return events


class RFAIEventProducer(BlockchainEventProducer):
    RFAI_EVENT_READ_BATCH_LIMIT = 50000

    def __init__(self, http_provider, repository=None):
        super().__init__(http_provider, "RFAI", repository)

    def _push_event(self, event):
        """
          `row_id` int(11) NOT NULL AUTO_INCREMENT,
          `block_no` int(11) NOT NULL,
          `event` varchar(256) NOT NULL,
          `json_str` text,
          `processed` bit(1) DEFAULT NULL,
          `transactionHash` varchar(256) DEFAULT NULL,
          `logIndex` varchar(256) DEFAULT NULL,
          `error_code` int(11) DEFAULT NULL,
          `error_msg` varchar(256) DEFAULT NULL,
          `row_updated` timestamp NULL DEFAULT NULL,
          `row_created` timestamp NULL DEFAULT NULL,
        :param event:
        :return:
        """

        block_number = event.blockNumber
        event_name = event.event
        json_str = str(dict(event.args))
        processed = 0
        transaction_hash = event.transactionHash.hex()
        log_index = event.logIndex
        error_code = 0
        error_message = ""
        event_type = EventType.RFAI.value

        self._event_repository.insert_raw_event(event_type, block_number, event_name, json_str, processed,
                                                transaction_hash, log_index, error_code, error_message)

    def _push_events_to_repository(self, events):
        for event in events:
            self._push_event(event)

    def produce_event(self, net_id):
        last_block_number = self._event_repository.read_last_read_block_number_for_event(self._contract_name)
        end_block_number = self._get_end_block_number(last_block_number, self.RFAI_EVENT_READ_BATCH_LIMIT)
        logger.info(f"reading mpe event from {last_block_number} to {end_block_number}")
        events = self._produce_contract_events(last_block_number, end_block_number, net_id)
        self._push_events_to_repository(events)
        self._event_repository.update_last_read_block_number_for_event(self._contract_name, end_block_number)
        return events


class TokenStakeEventProducer(BlockchainEventProducer):
    TOKEN_EVENT_READ_BATCH_LIMIT = 50000

    def __init__(self, http_provider, repository=None):
        super().__init__(http_provider, "TokenStake", repository)

    def _push_event(self, event):
        """
          `row_id` int(11) NOT NULL AUTO_INCREMENT,
          `block_no` int(11) NOT NULL,
          `event` varchar(256) NOT NULL,
          `json_str` text,
          `processed` bit(1) DEFAULT NULL,
          `transactionHash` varchar(256) DEFAULT NULL,
          `logIndex` varchar(256) DEFAULT NULL,
          `error_code` int(11) DEFAULT NULL,
          `error_msg` varchar(256) DEFAULT NULL,
          `row_updated` timestamp NULL DEFAULT NULL,
          `row_created` timestamp NULL DEFAULT NULL,
        :param event:
        :return:
        """

        block_number = event.blockNumber
        event_name = event.event
        json_str = str(dict(event.args))
        processed = 0
        transaction_hash = event.transactionHash.hex()
        log_index = event.logIndex
        error_code = 0
        error_message = ""
        event_type = EventType.TOKEN_STAKE.value

        self._event_repository.insert_raw_event(event_type, block_number, event_name, json_str, processed,
                                                transaction_hash, log_index, error_code, error_message)

    def _push_events_to_repository(self, events):
        for event in events:
            self._push_event(event)

    def produce_event(self, net_id):
        last_block_number = self._event_repository.read_last_read_block_number_for_event(self._contract_name)
        end_block_number = self._get_end_block_number(
            last_block_number, TokenStakeEventProducer.TOKEN_EVENT_READ_BATCH_LIMIT)
        logger.info(f"reading token stake event from {last_block_number} to {end_block_number}")
        events = self._produce_contract_events(last_block_number, end_block_number, net_id)
        self._push_events_to_repository(events)
        self._event_repository.update_last_read_block_number_for_event(self._contract_name, end_block_number)

        return events


class AirdropEventProducer(BlockchainEventProducer):
    AIRDROP_EVENT_READ_BATCH_LIMIT = 50000

    def __init__(self, http_provider, repository=None):
        super().__init__(http_provider, "SingularityAirdrop", repository)

    def _push_event(self, event):
        """
          `row_id` int(11) NOT NULL AUTO_INCREMENT,
          `block_no` int(11) NOT NULL,
          `event` varchar(256) NOT NULL,
          `json_str` text,
          `processed` bit(1) DEFAULT NULL,
          `transactionHash` varchar(256) DEFAULT NULL,
          `logIndex` varchar(256) DEFAULT NULL,
          `error_code` int(11) DEFAULT NULL,
          `error_msg` varchar(256) DEFAULT NULL,
          `row_updated` timestamp NULL DEFAULT NULL,
          `row_created` timestamp NULL DEFAULT NULL,
        :param event:
        :return:
        """

        block_number = event.blockNumber
        event_name = event.event
        json_str = str(dict(event.args))
        processed = 0
        transaction_hash = event.transactionHash.hex()
        log_index = event.logIndex
        error_code = 0
        error_message = ""
        event_type = EventType.SINGULARITYNET_AIRDROP.value

        self._event_repository.insert_raw_event(event_type, block_number, event_name, json_str, processed,
                                                transaction_hash, log_index, error_code, error_message)

    def _push_events_to_repository(self, events):
        for event in events:
            self._push_event(event)

    def produce_event(self, net_id):
        last_block_number = self._event_repository.read_last_read_block_number_for_event(self._contract_name)
        end_block_number = self._get_end_block_number(
            last_block_number, AirdropEventProducer.AIRDROP_EVENT_READ_BATCH_LIMIT)
        logger.info(f"reading airdrop event from {last_block_number} to {end_block_number}")
        events = self._produce_contract_events(last_block_number, end_block_number, net_id)
        self._push_events_to_repository(events)
        self._event_repository.update_last_read_block_number_for_event(self._contract_name, end_block_number)

        return events


class OccamAirdropEventProducer(BlockchainEventProducer):
    OCCAM_AIRDROP_EVENT_READ_BATCH_LIMIT = 50000

    def __init__(self, http_provider, repository=None):
        super().__init__(http_provider, "SingularityOccamAirdrop", repository)

    def _push_event(self, event):
        """
          `row_id` int(11) NOT NULL AUTO_INCREMENT,
          `block_no` int(11) NOT NULL,
          `event` varchar(256) NOT NULL,
          `json_str` text,
          `processed` bit(1) DEFAULT NULL,
          `transactionHash` varchar(256) DEFAULT NULL,
          `logIndex` varchar(256) DEFAULT NULL,
          `error_code` int(11) DEFAULT NULL,
          `error_msg` varchar(256) DEFAULT NULL,
          `row_updated` timestamp NULL DEFAULT NULL,
          `row_created` timestamp NULL DEFAULT NULL,
        :param event:
        :return:
        """

        block_number = event.blockNumber
        event_name = event.event
        json_str = str(dict(event.args))
        processed = 0
        transaction_hash = event.transactionHash.hex()
        log_index = event.logIndex
        error_code = 0
        error_message = ""
        event_type = EventType.OCCAM_SNET_AIRDROP.value

        self._event_repository.insert_raw_event(event_type, block_number, event_name, json_str, processed,
                                                transaction_hash, log_index, error_code, error_message)

    def _push_events_to_repository(self, events):
        for event in events:
            self._push_event(event)

    def produce_event(self, net_id):
        event_type = EventType.OCCAM_SNET_AIRDROP.value
        last_block_number = self._event_repository.read_last_read_block_number_for_event(
            event_type=EventType.OCCAM_SNET_AIRDROP.value)
        end_block_number = self._get_end_block_number(
            last_block_number, OccamAirdropEventProducer.OCCAM_AIRDROP_EVENT_READ_BATCH_LIMIT)
        logger.info(f"reading airdrop event from {last_block_number} to {end_block_number}")
        events = self._produce_contract_events(last_block_number, end_block_number, net_id)
        self._push_events_to_repository(events)
        self._event_repository.update_last_read_block_number_for_event(event_type=event_type,
                                                                       last_block_number=end_block_number)

        return events


class ConverterAGIXEventProducer(BlockchainEventProducer):
    CONVERTER_AGIX_EVENT_READ_BATCH_LIMIT = 50000

    def __init__(self, http_provider, repository=None):
        super().__init__(http_provider, "ConverterAGIX", repository)

    def _push_event(self, event):
        """
          `row_id` int(11) NOT NULL AUTO_INCREMENT,
          `block_no` int(11) NOT NULL,
          `event` varchar(256) NOT NULL,
          `json_str` text,
          `processed` bit(1) DEFAULT NULL,
          `transactionHash` varchar(256) DEFAULT NULL,
          `logIndex` varchar(256) DEFAULT NULL,
          `error_code` int(11) DEFAULT NULL,
          `error_msg` varchar(256) DEFAULT NULL,
          `row_updated` timestamp NULL DEFAULT NULL,
          `row_created` timestamp NULL DEFAULT NULL,
        :param event:
        :return:
        """

        block_number = event.blockNumber
        event_name = event.event
        json_str = str(dict(event.args))
        processed = 0
        transaction_hash = event.transactionHash.hex()
        log_index = event.logIndex
        error_code = 0
        error_message = ""
        event_type = EventType.CONVERTER_AGIX.value

        self._event_repository.insert_raw_event(event_type, block_number, event_name, json_str, processed,
                                                transaction_hash, log_index, error_code, error_message)

    def _push_events_to_repository(self, events):
        for event in events:
            self._push_event(event)

    def produce_event(self, net_id):
        last_block_number = self._event_repository.read_last_read_block_number_for_event(self._contract_name)
        end_block_number = self._get_end_block_number(
            last_block_number, ConverterAGIXEventProducer.CONVERTER_AGIX_EVENT_READ_BATCH_LIMIT)
        logger.info(f"reading converter agix event from {last_block_number} to {end_block_number}")
        events = self._produce_contract_events(last_block_number, end_block_number, net_id)
        self._push_events_to_repository(events)
        self._event_repository.update_last_read_block_number_for_event(self._contract_name, end_block_number)

        return events


class ConverterNTXEventProducer(BlockchainEventProducer):
    CONVERTER_NTX_EVENT_READ_BATCH_LIMIT = 500000

    def __init__(self, http_provider, repository=None):
        super().__init__(http_provider, "ConverterNTX", repository)

    def _push_event(self, event):
        """
          `row_id` int(11) NOT NULL AUTO_INCREMENT,
          `block_no` int(11) NOT NULL,
          `event` varchar(256) NOT NULL,
          `json_str` text,
          `processed` bit(1) DEFAULT NULL,
          `transactionHash` varchar(256) DEFAULT NULL,
          `logIndex` varchar(256) DEFAULT NULL,
          `error_code` int(11) DEFAULT NULL,
          `error_msg` varchar(256) DEFAULT NULL,
          `row_updated` timestamp NULL DEFAULT NULL,
          `row_created` timestamp NULL DEFAULT NULL,
        :param event:
        :return:
        """

        block_number = event.blockNumber
        event_name = event.event
        json_str = str(dict(event.args))
        processed = 0
        transaction_hash = event.transactionHash.hex()
        log_index = event.logIndex
        error_code = 0
        error_message = ""
        event_type = EventType.CONVERTER_NTX.value

        self._event_repository.insert_raw_event(event_type, block_number, event_name, json_str, processed,
                                                transaction_hash, log_index, error_code, error_message)

    def _push_events_to_repository(self, events):
        for event in events:
            self._push_event(event)

    def produce_event(self, net_id):
        last_block_number = self._event_repository.read_last_read_block_number_for_event(self._contract_name)
        end_block_number = self._get_end_block_number(
            last_block_number, ConverterNTXEventProducer.CONVERTER_NTX_EVENT_READ_BATCH_LIMIT)
        logger.info(f"Reading converter ntx event from {last_block_number} to {end_block_number}")
        events = self._produce_contract_events(last_block_number, end_block_number, net_id)
        self._push_events_to_repository(events)
        self._event_repository.update_last_read_block_number_for_event(self._contract_name, end_block_number)

        return events


class ConverterRJVEventProducer(BlockchainEventProducer):
    CONVERTER_RJV_EVENT_READ_BATCH_LIMIT = 500000

    def __init__(self, http_provider, repository=None):
        super().__init__(http_provider, "ConverterRJV", repository)

    def _push_event(self, event):
        """
          `row_id` int(11) NOT NULL AUTO_INCREMENT,
          `block_no` int(11) NOT NULL,
          `event` varchar(256) NOT NULL,
          `json_str` text,
          `processed` bit(1) DEFAULT NULL,
          `transactionHash` varchar(256) DEFAULT NULL,
          `logIndex` varchar(256) DEFAULT NULL,
          `error_code` int(11) DEFAULT NULL,
          `error_msg` varchar(256) DEFAULT NULL,
          `row_updated` timestamp NULL DEFAULT NULL,
          `row_created` timestamp NULL DEFAULT NULL,
        :param event:
        :return:
        """

        block_number = event.blockNumber
        event_name = event.event
        json_str = str(dict(event.args))
        processed = 0
        transaction_hash = event.transactionHash.hex()
        log_index = event.logIndex
        error_code = 0
        error_message = ""
        event_type = EventType.CONVERTER_RJV.value

        self._event_repository.insert_raw_event(event_type, block_number, event_name, json_str, processed,
                                                transaction_hash, log_index, error_code, error_message)

    def _push_events_to_repository(self, events):
        for event in events:
            self._push_event(event)

    def produce_event(self, net_id):
        last_block_number = self._event_repository.read_last_read_block_number_for_event(self._contract_name)
        end_block_number = self._get_end_block_number(
            last_block_number, ConverterRJVEventProducer.CONVERTER_RJV_EVENT_READ_BATCH_LIMIT)
        logger.info(f"Reading converter rjv event from {last_block_number} to {end_block_number}")
        events = self._produce_contract_events(last_block_number, end_block_number, net_id)
        self._push_events_to_repository(events)
        self._event_repository.update_last_read_block_number_for_event(self._contract_name, end_block_number)

        return events


class ConverterCGVEventProducer(BlockchainEventProducer):
    CONVERTER_CGV_EVENT_READ_BATCH_LIMIT = 500000

    def __init__(self, http_provider, repository=None):
        super().__init__(http_provider, "ConverterCGV", repository)

    def _push_event(self, event):
        """
          `row_id` int(11) NOT NULL AUTO_INCREMENT,
          `block_no` int(11) NOT NULL,
          `event` varchar(256) NOT NULL,
          `json_str` text,
          `processed` bit(1) DEFAULT NULL,
          `transactionHash` varchar(256) DEFAULT NULL,
          `logIndex` varchar(256) DEFAULT NULL,
          `error_code` int(11) DEFAULT NULL,
          `error_msg` varchar(256) DEFAULT NULL,
          `row_updated` timestamp NULL DEFAULT NULL,
          `row_created` timestamp NULL DEFAULT NULL,
        :param event:
        :return:
        """

        block_number = event.blockNumber
        event_name = event.event
        json_str = str(dict(event.args))
        processed = 0
        transaction_hash = event.transactionHash.hex()
        log_index = event.logIndex
        error_code = 0
        error_message = ""
        event_type = EventType.CONVERTER_CGV.value

        self._event_repository.insert_raw_event(event_type, block_number, event_name, json_str, processed,
                                                transaction_hash, log_index, error_code, error_message)

    def _push_events_to_repository(self, events):
        for event in events:
            self._push_event(event)

    def produce_event(self, net_id):
        last_block_number = self._event_repository.read_last_read_block_number_for_event(self._contract_name)
        end_block_number = self._get_end_block_number(
            last_block_number, ConverterCGVEventProducer.CONVERTER_CGV_EVENT_READ_BATCH_LIMIT)
        logger.info(f"Reading converter cgv event from {last_block_number} to {end_block_number}")
        events = self._produce_contract_events(last_block_number, end_block_number, net_id)
        self._push_events_to_repository(events)
        self._event_repository.update_last_read_block_number_for_event(self._contract_name, end_block_number)

        return events
