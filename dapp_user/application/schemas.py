import json
from typing import List

from common.constant import PayloadAssertionError, RequestPayloadType
from common.exceptions import BadRequestException
from dapp_user.constant import (
    CommunicationType,
    PreferenceType,
    SourceDApp,
    Status,
)
from pydantic import BaseModel, ConfigDict, Field, ValidationError


class AddOrUpdateUserPreferenceRequest(BaseModel):
    communication_type: CommunicationType = Field(..., alias="communicationType")
    preference_type: PreferenceType = Field(..., alias="preferenceType")
    source: SourceDApp = Field(..., alias="source")
    status: Status = Field(..., alias="status")
    opt_out_reason: str | None = Field(None, alias="optOutReason")

    model_config = ConfigDict(
        populate_by_name=True,
    )


class AddOrUpdateUserPreferencesRequest(BaseModel):
    user_preferences: List[AddOrUpdateUserPreferenceRequest] = Field(
        ..., min_length=1, alias="userPreferences"
    )

    model_config = ConfigDict(
        populate_by_name=True,
    )

    @classmethod
    def validate_event(cls, event: dict) -> "AddOrUpdateUserPreferencesRequest":
        try:
            assert event.get(RequestPayloadType.BODY) is not None, (
                PayloadAssertionError.MISSING_BODY
            )
            body = json.loads(event[RequestPayloadType.BODY])
            return cls.model_validate(body)

        except ValidationError as e:
            formatted_errors = [
                {"field": ".".join(str(loc) for loc in err["loc"]), "message": err["msg"]}
                for err in e.errors()
            ]
            raise BadRequestException(
                message="Validation failed for request body.",
                details={"validation_errors": formatted_errors},
            )
        except AssertionError as e:
            raise BadRequestException(message=str(e))
        except Exception:
            raise BadRequestException(message="Error while parsing payload")


class DeleteUserRequest(BaseModel):
    username: str | None = None

    @classmethod
    def validate_event(cls, event: dict) -> "DeleteUserRequest":
        try:
            data = event.get(RequestPayloadType.QUERY_STRING)
            return cls.model_validate(data if data else {})
        except ValidationError as e:
            formatted_errors = [
                {"field": ".".join(str(loc) for loc in err["loc"]), "message": err["msg"]}
                for err in e.errors()
            ]
            raise BadRequestException(
                message="Validation failed for request body.",
                details={"validation_erros": formatted_errors},
            )
        except AssertionError as e:
            raise BadRequestException(message=str(e))
        except Exception:
            raise BadRequestException(message="Error while parsing payload")


class CognitoUserAttributes(BaseModel):
    sub: str
    email: str
    email_verified: bool


class CognitoRequest(BaseModel):
    user_attributes: CognitoUserAttributes = Field(..., alias="userAttributes")

    model_config = ConfigDict(
        populate_by_name=True,
    )


class CognitoCallerContext(BaseModel):
    aws_sdk_version: str = Field(..., alias="awsSdkVersion")
    client_id: str = Field(..., alias="clientId")

    model_config = ConfigDict(
        populate_by_name=True,
    )


class CognitoUserPoolEvent(BaseModel):
    version: str
    trigger_source: str = Field(..., alias="triggerSource")
    region: str
    user_pool_id: str = Field(..., alias="userPoolId")
    name: str = Field(..., alias="userName")
    caller_context: CognitoCallerContext = Field(..., alias="callerContext")
    request: CognitoRequest

    model_config = ConfigDict(
        populate_by_name=True,
    )


class UpdateUserAlertsRequest(BaseModel):
    email_alerts: bool = Field(..., alias="emailAlerts")

    model_config = ConfigDict(
        populate_by_name=True,
    )

    @classmethod
    def validate_event(cls, event: dict) -> "UpdateUserAlertsRequest":
        try:
            assert event.get(RequestPayloadType.BODY) is not None, (
                PayloadAssertionError.MISSING_BODY
            )
            body = json.loads(event[RequestPayloadType.BODY])
            return cls.model_validate(body)

        except ValidationError as e:
            formatted_errors = [
                {"field": ".".join(str(loc) for loc in err["loc"]), "message": err["msg"]}
                for err in e.errors()
            ]
            raise BadRequestException(
                message="Validation failed for request body.",
                details={"validation_erros": formatted_errors},
            )
        except AssertionError as e:
            raise BadRequestException(message=str(e))
        except Exception:
            raise BadRequestException(message="Error while parsing payload")


class GetUserFeedbackRequest(BaseModel):
    org_id: str = Field(..., alias="orgId")
    service_id: str = Field(..., alias="serviceId")

    model_config = ConfigDict(
        populate_by_name=True,
    )

    @classmethod
    def validate_event(cls, event: dict) -> "GetUserFeedbackRequest":
        try:
            data = event.get(RequestPayloadType.QUERY_STRING)
            return cls.model_validate(data)
        except ValidationError as e:
            formatted_errors = [
                {"field": ".".join(str(loc) for loc in err["loc"]), "message": err["msg"]}
                for err in e.errors()
            ]
            raise BadRequestException(
                message="Validation failed for request body.",
                details={"validation_erros": formatted_errors},
            )
        except Exception:
            raise BadRequestException(message="Error while parsing payload")


class CreateUserServiceReviewRequest(BaseModel):
    org_id: str = Field(..., alias="orgId")
    service_id: str = Field(..., alias="serviceId")
    user_rating: float = Field(..., alias="userRating")
    comment: str | None = None

    model_config = ConfigDict(
        populate_by_name=True,
    )

    @classmethod
    def validate_event(cls, event: dict) -> "CreateUserServiceReviewRequest":
        try:
            assert event.get(RequestPayloadType.BODY) is not None, (
                PayloadAssertionError.MISSING_BODY
            )
            body = json.loads(event[RequestPayloadType.BODY])
            return cls.model_validate(body)

        except ValidationError as e:
            formatted_errors = [
                {"field": ".".join(str(loc) for loc in err["loc"]), "message": err["msg"]}
                for err in e.errors()
            ]
            raise BadRequestException(
                message="Validation failed for request body.",
                details={"validation_erros": formatted_errors},
            )
        except AssertionError as e:
            raise BadRequestException(message=str(e))
        except Exception:
            raise BadRequestException(message="Error while parsing payload")
