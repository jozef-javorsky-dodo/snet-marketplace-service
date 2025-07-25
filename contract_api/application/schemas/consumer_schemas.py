import ast
from pydantic import BaseModel, model_validator, Field, field_validator
import json
from web3 import Web3

from common.validation_handler import validation_handler


class EventConsumerRequest(BaseModel):
    event_name: str = Field(alias = "name")

    @classmethod
    def get_events_from_queue(cls, event: dict):
        converted_events = []
        records = event.get("Records", [])
        if records:
            for record in records:
                body = record.get("body")
                if body:
                    parsed_body = json.loads(body)
                    message = parsed_body.get("Message")
                    if message:
                        payload = json.loads(message)
                        converted_events.append(payload["blockchain_event"])
        return converted_events

    @classmethod
    def convert_data(cls, data: dict) -> dict:
        converted_data = {
            "name": data["name"],
            **ast.literal_eval(data["data"]["json_str"])
        }
        return converted_data


class MpeEventConsumerRequest(EventConsumerRequest):
    channel_id: int = Field(alias = "channelId")
    group_id: bytes = Field(alias = "groupId", default = None)
    sender: str | None = None
    signer: str | None = None
    recipient: str | None = None
    nonce: int | None = None
    expiration: int | None = None
    amount: int | None = None

    @classmethod
    @validation_handler()
    def validate_event(cls, event: dict) -> "MpeEventConsumerRequest":
        return cls.model_validate(event)

    @model_validator(mode = "before")
    @classmethod
    def convert_data_types(cls, data: dict) -> dict:
        data = cls.convert_data(data)
        return data


class RegistryEventConsumerRequest(EventConsumerRequest):
    org_id: str = Field(alias = "orgId")
    service_id: str | None = Field(alias = "serviceId", default = None)
    metadata_uri: str | None = Field(alias = "metadataURI", default = None)

    @classmethod
    @validation_handler()
    def validate_event(cls, event: dict) -> "RegistryEventConsumerRequest":
        return cls.model_validate(event)

    @model_validator(mode = "before")
    @classmethod
    def convert_data_types(cls, data: dict) -> dict:
        data = cls.convert_data(data)
        converted_data = {}
        for key, value in data.items():
            new_value = value
            if key != "name":
                new_value = Web3.to_text(value).rstrip("\x00")
            converted_data[key] = new_value
        return converted_data
