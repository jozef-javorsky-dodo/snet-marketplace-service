import json
import unittest
from unittest.mock import patch

from signer.application import handlers


class TestSignUPAPI(unittest.TestCase):
    def setUp(self):
        pass

    @patch("common.blockchain_util.BlockChainUtil.get_current_block_no")
    @patch("common.blockchain_util.BlockChainUtil.read_contract_address")
    @patch("boto3.client")
    def test_signature_for_state_service(
        self, mock_boto_client, mock_read_contract_address, mock_current_block_no
    ):
        signature_for_state_service = {
            "body": '{"channel_id": 1}',
            "requestContext": {
                "stage": "ropsten",
                "authorizer": {"claims": {"email": "dummy@dummy.com"}},
            },
            "headers": {"origin": "testnet.marketplace-api"}
        }
        mock_read_contract_address.return_value = "0x8FB1dC8df86b388C7e00689d1eCb533A160B4D0C"
        mock_current_block_no.return_value = 6521925
        response = handlers.get_state_service_signature_handler(
            event=signature_for_state_service, context=None
        )
        assert response["statusCode"] == 200
        response_body = json.loads(response["body"])
        assert response_body["status"] == "success"
        assert (
            response_body["data"]["signature"]
            == "f4fad486513c6e514869a2af9423de3c1e03c9953b4cd79c4d78f7f8f54da1a01812d7c58120c038ead631e2462ab788746972cad46f4e7f2f1bd79b863b54681c"
        )
        assert (
            response_body["data"]["snet-current-block-number"] == mock_current_block_no.return_value
        )

    @patch("common.blockchain_util.BlockChainUtil.get_current_block_no")
    @patch("common.blockchain_util.BlockChainUtil.read_contract_address")
    @patch("boto3.client")
    def test_signature_for_regular_call(
        self, mock_boto_client, mock_read_contract_address, mock_current_block_no
    ):
        signature_for_regular_call = {
            "body": '{"channel_id": 1, "nonce": 6487832, "amount": 1}',
            "requestContext": {
                "stage": "ropsten",
                "authorizer": {"claims": {"email": "dummy@dummy.com"}},
            },
            "headers": {"origin": "testnet.marketplace"},
        }
        mock_current_block_no.return_value = 6521925
        mock_read_contract_address.return_value = "0x8FB1dC8df86b388C7e00689d1eCb533A160B4D0C"
        response = handlers.get_regular_call_signature_handler(
            event=signature_for_regular_call, context=None
        )
        assert response["statusCode"] == 200
        response_body = json.loads(response["body"])
        assert response_body["status"] == "success"
        assert (
            response_body["data"]["snet-payment-channel-signature-bin"]
            == "505dec3d328eced279a2953e7ba614936a239fb558c80615ff1c97115f8b76ea0530dc47acab7bca8c1dd4563f0299d9b1f61933902919097d82eb0eeb12cb501c"
        )
        assert response_body["data"]["snet-payment-type"] == "escrow"
        assert response_body["data"]["snet-payment-channel-id"] == 1
        assert response_body["data"]["snet-payment-channel-nonce"] == 6487832
        assert response_body["data"]["snet-payment-channel-amount"] == 1
        assert (
            response_body["data"]["snet-current-block-number"] == mock_current_block_no.return_value
        )

    @patch("common.blockchain_util.BlockChainUtil.get_current_block_no")
    @patch("common.blockchain_util.BlockChainUtil.read_contract_address")
    @patch("boto3.client")
    def test_signature_for_open_channel_for_third_party(
        self, mock_boto_client, mock_read_contract_address, mock_current_block_no
    ):
        signature_for_open_channel_for_third_party = {
            "body": '{"recipient": "0x9c302750c50307D3Ad88eaA9a6506874a15cE4Cb", "group_id" : "0x0d2d8ea0a49f184ffb8403bfd36de9b25e10763d0c26f62cade25b0a80075527", "amount_in_cogs" : 10, "expiration": 7487832, "message_nonce": 6487832, "signer_key": "7df9964a4f39bb035ea1c1474283348582150e363f78330de7b941577caaafa3", "executor_wallet_address": "0x3Bb9b2499c283cec176e7C707Ecb495B7a961ebf"}',
            "requestContext": {
                "stage": "ropsten",
                "authorizer": {"claims": {"email": "dummy@dummy.com"}},
            },
            "headers": {"origin": "testnet.marketplace-api"}
        }
        mock_read_contract_address.return_value = "0x8FB1dC8df86b388C7e00689d1eCb533A160B4D0C"
        mock_current_block_no.return_value = 6521925
        response = handlers.get_open_channel_for_third_party_signature_handler(
            event=signature_for_open_channel_for_third_party, context=None
        )
        assert response["statusCode"] == 200
        response_body = json.loads(response["body"])
        print(response_body)
        assert response_body["status"] == "success"
        assert (
            response_body["data"]["r"]
            == "6057e2706d63351e774eaf56616afa7c138129b27b0dfd121457761d4267c3b82f"
        )
        assert (
            response_body["data"]["s"]
            == "0x2b98ae088f6e5d4737fae8beba95c7203d33c07baaeccbb8eea5a6c361ae841b"
        )
        assert response_body["data"]["v"] == 27
        assert (
            response_body["data"]["signature"]
            == "6057e2706d63351e774eaf56616afa7c138129b27b0dfd121457761d4267c3b82f2b98ae088f6e5d4737fae8beba95c7203d33c07baaeccbb8eea5a6c361ae841b"
        )
