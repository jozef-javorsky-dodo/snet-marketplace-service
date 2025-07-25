# -*- coding: utf-8 -*-
# Generated by the protocol buffer compiler.  DO NOT EDIT!
# NO CHECKED-IN PROTOBUF GENCODE
# source: state_service.proto
# Protobuf Python Version: 5.29.0
"""Generated protocol buffer code."""

from google.protobuf import descriptor as _descriptor
from google.protobuf import descriptor_pool as _descriptor_pool
from google.protobuf import runtime_version as _runtime_version
from google.protobuf import symbol_database as _symbol_database
from google.protobuf.internal import builder as _builder

_runtime_version.ValidateProtobufRuntimeVersion(
    _runtime_version.Domain.PUBLIC, 5, 29, 0, "", "state_service.proto"
)
# @@protoc_insertion_point(imports)

_sym_db = _symbol_database.Default()


DESCRIPTOR = _descriptor_pool.Default().AddSerializedFile(
    b'\n\x13state_service.proto\x12\x06\x65scrow"S\n\x13\x43hannelStateRequest\x12\x12\n\nchannel_id\x18\x01 \x01(\x0c\x12\x11\n\tsignature\x18\x02 \x01(\x0c\x12\x15\n\rcurrent_block\x18\x03 \x01(\x04"\xcf\x01\n\x11\x43hannelStateReply\x12\x15\n\rcurrent_nonce\x18\x01 \x01(\x0c\x12\x1d\n\x15\x63urrent_signed_amount\x18\x02 \x01(\x0c\x12\x19\n\x11\x63urrent_signature\x18\x03 \x01(\x0c\x12\x1f\n\x17old_nonce_signed_amount\x18\x04 \x01(\x0c\x12\x1b\n\x13old_nonce_signature\x18\x05 \x01(\x0c\x12\x16\n\x0eplanned_amount\x18\x06 \x01(\x04\x12\x13\n\x0bused_amount\x18\x07 \x01(\x04"\xba\x01\n\x17GetFreeCallTokenRequest\x12\x0f\n\x07\x61\x64\x64ress\x18\x01 \x01(\t\x12\x11\n\tsignature\x18\x02 \x01(\x0c\x12\x15\n\rcurrent_block\x18\x03 \x01(\x04\x12\x14\n\x07user_id\x18\x04 \x01(\tH\x00\x88\x01\x01\x12%\n\x18token_lifetime_in_blocks\x18\x05 \x01(\x04H\x01\x88\x01\x01\x42\n\n\x08_user_idB\x1b\n\x19_token_lifetime_in_blocks"Q\n\rFreeCallToken\x12\r\n\x05token\x18\x01 \x01(\x0c\x12\x11\n\ttoken_hex\x18\x02 \x01(\t\x12\x1e\n\x16token_expiration_block\x18\x03 \x01(\x04"\x8c\x01\n\x14\x46reeCallStateRequest\x12\x0f\n\x07\x61\x64\x64ress\x18\x01 \x01(\t\x12\x14\n\x07user_id\x18\x02 \x01(\tH\x00\x88\x01\x01\x12\x17\n\x0f\x66ree_call_token\x18\x03 \x01(\x0c\x12\x11\n\tsignature\x18\x04 \x01(\x0c\x12\x15\n\rcurrent_block\x18\x05 \x01(\x04\x42\n\n\x08_user_id"2\n\x12\x46reeCallStateReply\x12\x1c\n\x14\x66ree_calls_available\x18\x01 \x01(\x04\x32i\n\x1aPaymentChannelStateService\x12K\n\x0fGetChannelState\x12\x1b.escrow.ChannelStateRequest\x1a\x19.escrow.ChannelStateReply"\x00\x32\xb9\x01\n\x14\x46reeCallStateService\x12S\n\x15GetFreeCallsAvailable\x12\x1c.escrow.FreeCallStateRequest\x1a\x1a.escrow.FreeCallStateReply"\x00\x12L\n\x10GetFreeCallToken\x12\x1f.escrow.GetFreeCallTokenRequest\x1a\x15.escrow.FreeCallToken"\x00\x42,\n\x1fio.singularitynet.daemon.escrowZ\t../escrowb\x06proto3'
)

_globals = globals()
_builder.BuildMessageAndEnumDescriptors(DESCRIPTOR, _globals)
_builder.BuildTopDescriptorsAndMessages(DESCRIPTOR, "state_service_pb2", _globals)
if not _descriptor._USE_C_DESCRIPTORS:
    _globals["DESCRIPTOR"]._loaded_options = None
    _globals[
        "DESCRIPTOR"
    ]._serialized_options = b"\n\037io.singularitynet.daemon.escrowZ\t../escrow"
    _globals["_CHANNELSTATEREQUEST"]._serialized_start = 31
    _globals["_CHANNELSTATEREQUEST"]._serialized_end = 114
    _globals["_CHANNELSTATEREPLY"]._serialized_start = 117
    _globals["_CHANNELSTATEREPLY"]._serialized_end = 324
    _globals["_GETFREECALLTOKENREQUEST"]._serialized_start = 327
    _globals["_GETFREECALLTOKENREQUEST"]._serialized_end = 513
    _globals["_FREECALLTOKEN"]._serialized_start = 515
    _globals["_FREECALLTOKEN"]._serialized_end = 596
    _globals["_FREECALLSTATEREQUEST"]._serialized_start = 599
    _globals["_FREECALLSTATEREQUEST"]._serialized_end = 739
    _globals["_FREECALLSTATEREPLY"]._serialized_start = 741
    _globals["_FREECALLSTATEREPLY"]._serialized_end = 791
    _globals["_PAYMENTCHANNELSTATESERVICE"]._serialized_start = 793
    _globals["_PAYMENTCHANNELSTATESERVICE"]._serialized_end = 898
    _globals["_FREECALLSTATESERVICE"]._serialized_start = 901
    _globals["_FREECALLSTATESERVICE"]._serialized_end = 1086
# @@protoc_insertion_point(module_scope)
