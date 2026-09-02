"""
Razorpay Gateway Adapter Tests — Step 14.

All tests use mocked HTTP — NO real Razorpay API calls during normal pytest.
Integration tests (real API) are in tests/integration/test_razorpay_test_mode.py
and require RAZORPAY_KEY_ID to be set; they are marked @pytest.mark.razorpay_integration.

28 tests covering:
- Provider configuration and mode resolution
- Razorpay client authentication and request building
- Payment fetch, order fetch, order payments fetch
- Payment link creation
- HTTP error handling (400, 401, 403, 404, 429, 500, timeout, malformed JSON)
- Webhook signature validation
- Webhook event normalization
- Provider mode hard blocks
- Live mode enforcement
"""

import sys
import os
import json
import hmac
import hashlib
import unittest
from pathlib import Path
from unittest.mock import patch, MagicMock, PropertyMock
from io import BytesIO
from urllib.error import HTTPError, URLError

# Add src to Python path for all tests
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))



# ---------------------------------------------------------------------------
# Test 1: Provider Mode Default (SIMULATION)
# ---------------------------------------------------------------------------

class TestProviderModeDefault:
    def test_default_mode_is_simulation(self, monkeypatch):
        monkeypatch.delenv("RECOVERAI_PROVIDER_MODE", raising=False)
        monkeypatch.delenv("PAYMENT_PROVIDER", raising=False)
        from gateway.provider_config import get_provider_mode, ProviderMode
        assert get_provider_mode() == ProviderMode.SIMULATION


# ---------------------------------------------------------------------------
# Test 2: Provider Mode — RAZORPAY_TEST
# ---------------------------------------------------------------------------

class TestProviderModeRazorpayTest:
    def test_razorpay_test_mode(self, monkeypatch):
        monkeypatch.setenv("RECOVERAI_PROVIDER_MODE", "razorpay_test")
        from importlib import reload
        import gateway.provider_config as pc
        reload(pc)
        from gateway.provider_config import get_provider_mode, ProviderMode
        assert get_provider_mode() == ProviderMode.RAZORPAY_TEST

    def test_unknown_mode_defaults_to_simulation(self, monkeypatch):
        monkeypatch.setenv("RECOVERAI_PROVIDER_MODE", "unknown_mode_xyz")
        from gateway.provider_config import get_provider_mode, ProviderMode
        assert get_provider_mode() == ProviderMode.SIMULATION


# ---------------------------------------------------------------------------
# Test 3: Provider Capabilities — SIMULATION mode
# ---------------------------------------------------------------------------

class TestSimulationCapabilities:
    def test_simulation_has_no_live_execution(self):
        from gateway.provider_config import get_capabilities, ProviderMode
        caps = get_capabilities(ProviderMode.SIMULATION)
        assert caps.live_money_execution is False

    def test_simulation_has_no_signature_verification(self):
        from gateway.provider_config import get_capabilities, ProviderMode
        caps = get_capabilities(ProviderMode.SIMULATION)
        assert caps.verify_webhook_signature is False

    def test_razorpay_test_has_signature_verification(self):
        from gateway.provider_config import get_capabilities, ProviderMode
        caps = get_capabilities(ProviderMode.RAZORPAY_TEST)
        assert caps.verify_webhook_signature is True
        assert caps.live_money_execution is False


# ---------------------------------------------------------------------------
# Test 4: Live Mode Hard Block
# ---------------------------------------------------------------------------

class TestLiveModeHardBlock:
    def test_razorpay_live_raises_on_construction(self, monkeypatch):
        monkeypatch.setenv("RECOVERAI_PROVIDER_MODE", "razorpay_live")
        from gateway.provider_config import LiveModeDisabledError, ProviderMode
        from gateway.razorpay_adapter import RazorpayGatewayAdapter
        try:
            adapter = RazorpayGatewayAdapter(mode=ProviderMode.RAZORPAY_LIVE)
            assert False, "Should have raised LiveModeDisabledError"
        except LiveModeDisabledError as exc:
            assert "LIVE PAYMENT EXECUTION IS DISABLED" in str(exc)

    def test_live_transactions_env_raises(self, monkeypatch):
        monkeypatch.setenv("RECOVERAI_LIVE_TRANSACTIONS", "true")
        from gateway.provider_config import assert_live_execution_disabled, LiveModeDisabledError, ProviderMode
        try:
            assert_live_execution_disabled(ProviderMode.SIMULATION)
            assert False, "Should have raised LiveModeDisabledError"
        except LiveModeDisabledError as exc:
            assert "LIVE PAYMENT EXECUTION IS DISABLED" in str(exc)


# ---------------------------------------------------------------------------
# Test 5: Razorpay Client — Missing Credentials
# ---------------------------------------------------------------------------

class TestRazorpayClientMissingCredentials:
    def test_raises_on_missing_credentials(self, monkeypatch):
        monkeypatch.delenv("RAZORPAY_KEY_ID", raising=False)
        monkeypatch.delenv("RAZORPAY_KEY_SECRET", raising=False)
        from gateway.razorpay_client import RazorpayClient, RazorpayClientError
        try:
            RazorpayClient(key_id="", key_secret="")
            assert False, "Should have raised RazorpayClientError"
        except RazorpayClientError as exc:
            assert "not configured" in str(exc).lower()


# ---------------------------------------------------------------------------
# Test 6: Razorpay Client — Auth Header
# ---------------------------------------------------------------------------

class TestRazorpayClientAuth:
    def test_auth_header_uses_basic_auth(self):
        from gateway.razorpay_client import RazorpayClient
        import base64
        client = RazorpayClient(key_id="rzp_test_abc123", key_secret="test_secret_xyz")
        auth = client._auth_header()
        assert auth.startswith("Basic ")
        decoded = base64.b64decode(auth[6:]).decode("utf-8")
        assert decoded == "rzp_test_abc123:test_secret_xyz"

    def test_masked_key_id_redacts_secret(self):
        from gateway.razorpay_client import RazorpayClient
        client = RazorpayClient(key_id="rzp_test_abc123", key_secret="super_secret_key")
        masked = client._masked_key_id()
        assert "super_secret_key" not in masked
        assert "***" in masked


# ---------------------------------------------------------------------------
# Test 7: Razorpay Client — Payment Fetch Success
# ---------------------------------------------------------------------------

class TestRazorpayFetchPaymentSuccess:
    def test_fetch_payment_success(self):
        from gateway.razorpay_client import RazorpayClient
        from gateway.razorpay_models import RazorpayPayment

        payment_data = {
            "id": "pay_test123",
            "order_id": "order_test456",
            "amount": 50000,
            "currency": "INR",
            "status": "failed",
            "captured": False,
            "method": "upi",
            "error_code": "BAD_REQUEST_ERROR",
            "error_description": "VPA is invalid",
        }

        client = RazorpayClient(key_id="rzp_test_x", key_secret="secret_y")

        with patch.object(client, "_request", return_value=payment_data):
            payment = client.fetch_payment("pay_test123")
            assert isinstance(payment, RazorpayPayment)
            assert payment.id == "pay_test123"
            assert payment.amount_inr == 500.0
            assert payment.is_failed is True
            assert payment.is_captured is False


# ---------------------------------------------------------------------------
# Test 8: Razorpay Client — Order Fetch Success
# ---------------------------------------------------------------------------

class TestRazorpayFetchOrderSuccess:
    def test_fetch_order_success(self):
        from gateway.razorpay_client import RazorpayClient
        from gateway.razorpay_models import RazorpayOrder

        order_data = {
            "id": "order_test456",
            "amount": 50000,
            "amount_paid": 0,
            "amount_due": 50000,
            "currency": "INR",
            "status": "attempted",
            "attempts": 1,
        }

        client = RazorpayClient(key_id="rzp_test_x", key_secret="secret_y")

        with patch.object(client, "_request", return_value=order_data):
            order = client.fetch_order("order_test456")
            assert isinstance(order, RazorpayOrder)
            assert order.id == "order_test456"
            assert order.amount_inr == 500.0
            assert order.is_paid is False


# ---------------------------------------------------------------------------
# Test 9: Razorpay Client — Order Payments Fetch
# ---------------------------------------------------------------------------

class TestRazorpayFetchOrderPayments:
    def test_fetch_order_payments_success(self):
        from gateway.razorpay_client import RazorpayClient
        from gateway.razorpay_models import RazorpayOrderPayments

        data = {
            "entity": "collection",
            "count": 1,
            "items": [
                {
                    "id": "pay_test789",
                    "amount": 50000,
                    "currency": "INR",
                    "status": "failed",
                    "captured": False,
                }
            ],
        }

        client = RazorpayClient(key_id="rzp_test_x", key_secret="secret_y")

        with patch.object(client, "_request", return_value=data):
            result = client.fetch_order_payments("order_test456")
            assert isinstance(result, RazorpayOrderPayments)
            assert result.count == 1
            assert result.items[0].id == "pay_test789"


# ---------------------------------------------------------------------------
# Test 10: Razorpay Client — Payment Link Creation
# ---------------------------------------------------------------------------

class TestRazorpayCreatePaymentLink:
    def test_create_payment_link_success(self):
        from gateway.razorpay_client import RazorpayClient
        from gateway.razorpay_models import RazorpayPaymentLink, RazorpayPaymentLinkRequest

        link_data = {
            "id": "plink_test001",
            "short_url": "https://rzp.io/l/testlink",
            "amount": 50000,
            "currency": "INR",
            "status": "created",
            "reference_id": "pay_failedXYZ",
        }

        client = RazorpayClient(key_id="rzp_test_x", key_secret="secret_y")

        with patch.object(client, "_request", return_value=link_data):
            request = RazorpayPaymentLinkRequest(amount=50000)
            result = client.create_payment_link(request)
            assert isinstance(result, RazorpayPaymentLink)
            assert result.id == "plink_test001"
            assert result.short_url == "https://rzp.io/l/testlink"
            assert result.amount_inr == 500.0
            assert result.is_active is True

    def test_payment_link_does_not_retry(self):
        """Payment link creation must NOT be retried to avoid duplicate links."""
        from gateway.razorpay_client import RazorpayClient, RazorpayPaymentLinkRequest
        from gateway.razorpay_models import RazorpayPaymentLinkRequest as RPLR

        client = RazorpayClient(key_id="rzp_test_x", key_secret="secret_y")
        calls = []

        def mock_request(method, path, body=None, correlation_id=None, retry=False):
            calls.append({"retry": retry})
            return {
                "id": "plink_x",
                "amount": 1000,
                "currency": "INR",
                "status": "created",
            }

        with patch.object(client, "_request", side_effect=mock_request):
            request = RPLR(amount=1000)
            client.create_payment_link(request)
            # Must call with retry=False
            assert calls[0]["retry"] is False


# ---------------------------------------------------------------------------
# Test 11: HTTP 401 Authentication Error
# ---------------------------------------------------------------------------

class TestRazorpayHttp401:
    def test_http_401_raises_auth_error(self):
        from gateway.razorpay_client import RazorpayClient, RazorpayAuthError

        error_body = json.dumps({"error": {"code": "BAD_REQUEST_ERROR", "description": "Invalid API key"}}).encode()
        http_error = HTTPError(
            url="https://api.razorpay.com/v1/payments/pay_x",
            code=401,
            msg="Unauthorized",
            hdrs=None,
            fp=BytesIO(error_body),
        )

        client = RazorpayClient(key_id="rzp_test_x", key_secret="wrong_secret")

        with patch("gateway.razorpay_client.urlopen", side_effect=http_error):
            try:
                client.fetch_payment("pay_x")
                assert False, "Should have raised RazorpayAuthError"
            except RazorpayAuthError as exc:
                assert exc.status_code == 401
                assert "authentication failed" in str(exc).lower()


# ---------------------------------------------------------------------------
# Test 12: HTTP 429 Rate Limit Error
# ---------------------------------------------------------------------------

class TestRazorpayHttp429:
    def test_http_429_raises_rate_limit_error(self):
        from gateway.razorpay_client import RazorpayClient, RazorpayRateLimitError

        error_body = json.dumps({"error": {"code": "RATE_LIMIT", "description": "Too many requests"}}).encode()
        http_error = HTTPError(
            url="https://api.razorpay.com/v1/payments/pay_x",
            code=429,
            msg="Too Many Requests",
            hdrs=None,
            fp=BytesIO(error_body),
        )

        client = RazorpayClient(key_id="rzp_test_x", key_secret="secret_y")

        with patch("gateway.razorpay_client.urlopen", side_effect=http_error):
            try:
                client.fetch_payment("pay_x")
                assert False, "Should have raised RazorpayRateLimitError"
            except RazorpayRateLimitError as exc:
                assert exc.status_code == 429


# ---------------------------------------------------------------------------
# Test 13: HTTP 404 Not Found
# ---------------------------------------------------------------------------

class TestRazorpayHttp404:
    def test_http_404_raises_not_found(self):
        from gateway.razorpay_client import RazorpayClient, RazorpayNotFoundError

        error_body = json.dumps({"error": {"code": "BAD_REQUEST_ERROR", "description": "Payment not found"}}).encode()
        http_error = HTTPError(
            url="https://api.razorpay.com/v1/payments/pay_nonexistent",
            code=404,
            msg="Not Found",
            hdrs=None,
            fp=BytesIO(error_body),
        )

        client = RazorpayClient(key_id="rzp_test_x", key_secret="secret_y")

        with patch("gateway.razorpay_client.urlopen", side_effect=http_error):
            try:
                client.fetch_payment("pay_nonexistent")
                assert False, "Should have raised RazorpayNotFoundError"
            except RazorpayNotFoundError as exc:
                assert exc.status_code == 404


# ---------------------------------------------------------------------------
# Test 14: HTTP 500 Server Error
# ---------------------------------------------------------------------------

class TestRazorpayHttp500:
    def test_http_500_raises_server_error(self):
        from gateway.razorpay_client import RazorpayClient, RazorpayServerError

        error_body = json.dumps({"error": {"code": "SERVER_ERROR", "description": "Internal error"}}).encode()
        http_error = HTTPError(
            url="https://api.razorpay.com/v1/payments/pay_x",
            code=500,
            msg="Internal Server Error",
            hdrs=None,
            fp=BytesIO(error_body),
        )

        client = RazorpayClient(key_id="rzp_test_x", key_secret="secret_y")

        with patch("gateway.razorpay_client.urlopen", side_effect=http_error):
            try:
                client.fetch_payment("pay_x")
                assert False, "Should have raised RazorpayServerError"
            except RazorpayServerError as exc:
                assert exc.status_code == 500


# ---------------------------------------------------------------------------
# Test 15: Timeout Error
# ---------------------------------------------------------------------------

class TestRazorpayTimeout:
    def test_timeout_raises_timeout_error(self):
        from gateway.razorpay_client import RazorpayClient, RazorpayTimeoutError

        timeout_err = URLError("timed out")

        client = RazorpayClient(key_id="rzp_test_x", key_secret="secret_y", timeout=0.001)

        with patch("gateway.razorpay_client.urlopen", side_effect=timeout_err):
            try:
                client.fetch_payment("pay_x")
                assert False, "Should have raised RazorpayTimeoutError"
            except RazorpayTimeoutError:
                pass


# ---------------------------------------------------------------------------
# Test 16: Malformed JSON
# ---------------------------------------------------------------------------

class TestRazorpayMalformedJson:
    def test_malformed_json_raises_error(self):
        from gateway.razorpay_client import RazorpayClient, RazorpayMalformedResponseError

        class MockResponse:
            status = 200
            def read(self):
                return b"Not JSON at all {{{{{}"
            def __enter__(self):
                return self
            def __exit__(self, *args):
                pass

        client = RazorpayClient(key_id="rzp_test_x", key_secret="secret_y")

        with patch("gateway.razorpay_client.urlopen", return_value=MockResponse()):
            try:
                client.fetch_payment("pay_x")
                assert False, "Should have raised RazorpayMalformedResponseError"
            except RazorpayMalformedResponseError:
                pass


# ---------------------------------------------------------------------------
# Test 17: Webhook Signature Validation — Valid
# ---------------------------------------------------------------------------

class TestWebhookSignatureValid:
    def test_valid_signature_passes(self):
        from gateway.razorpay_webhook import RazorpayWebhookSignatureValidator

        secret = "test_webhook_secret_abc"
        body = b'{"event":"payment.failed","id":"evt_001"}'
        expected_sig = hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()

        result = RazorpayWebhookSignatureValidator.validate(
            raw_body=body,
            signature=expected_sig,
            webhook_secret=secret,
        )
        assert result is True


# ---------------------------------------------------------------------------
# Test 18: Webhook Signature Validation — Invalid
# ---------------------------------------------------------------------------

class TestWebhookSignatureInvalid:
    def test_invalid_signature_fails(self):
        from gateway.razorpay_webhook import RazorpayWebhookSignatureValidator

        result = RazorpayWebhookSignatureValidator.validate(
            raw_body=b'{"event":"payment.failed"}',
            signature="definitely_wrong_signature_abc123",
            webhook_secret="test_secret",
        )
        assert result is False


# ---------------------------------------------------------------------------
# Test 19: Webhook Signature — Missing Secret
# ---------------------------------------------------------------------------

class TestWebhookSignatureMissingSecret:
    def test_missing_secret_raises_error(self, monkeypatch):
        monkeypatch.delenv("RAZORPAY_WEBHOOK_SECRET", raising=False)
        from gateway.razorpay_webhook import RazorpayWebhookSignatureValidator, RazorpaySignatureError

        try:
            RazorpayWebhookSignatureValidator.validate(
                raw_body=b"{}",
                signature="some_sig",
                webhook_secret="",
            )
            assert False, "Should have raised RazorpaySignatureError"
        except RazorpaySignatureError as exc:
            assert "RAZORPAY_WEBHOOK_SECRET" in str(exc)


# ---------------------------------------------------------------------------
# Test 20: Webhook Normalization — payment.failed
# ---------------------------------------------------------------------------

class TestWebhookNormalizationPaymentFailed:
    def test_payment_failed_normalization(self):
        from gateway.razorpay_webhook import RazorpayWebhookNormalizer

        payload = {
            "event": "payment.failed",
            "id": "evt_failed_001",
            "entity": "event",
            "contains": ["payment"],
            "payload": {
                "payment": {
                    "entity": {
                        "id": "pay_failedXYZ",
                        "order_id": "order_testABC",
                        "amount": 75000,
                        "currency": "INR",
                        "status": "failed",
                        "captured": False,
                        "method": "card",
                        "error_code": "BAD_REQUEST_ERROR",
                        "error_description": "Card declined",
                    }
                }
            },
        }

        webhook = RazorpayWebhookNormalizer.normalize(
            raw_payload=payload,
            provider_event_id="evt_failed_001",
            signature_verified=True,
        )
        assert webhook.event == "payment.failed"
        assert webhook.payment_id == "pay_failedXYZ"
        assert webhook.order_id == "order_testABC"
        assert webhook.amount == 750.0
        assert webhook.method == "card"
        assert webhook.provider == "razorpay"
        assert webhook.payload["signature_verified"] is True
        assert "UNTRUSTED_notes" in webhook.payload


# ---------------------------------------------------------------------------
# Test 21: Webhook Normalization — payment.authorized
# ---------------------------------------------------------------------------

class TestWebhookNormalizationPaymentAuthorized:
    def test_payment_authorized_normalization(self):
        from gateway.razorpay_webhook import RazorpayWebhookNormalizer

        payload = {
            "event": "payment.authorized",
            "id": "evt_auth_001",
            "entity": "event",
            "contains": ["payment"],
            "payload": {
                "payment": {
                    "entity": {
                        "id": "pay_authorizedABC",
                        "amount": 100000,
                        "currency": "INR",
                        "status": "authorized",
                        "captured": False,
                        "method": "upi",
                    }
                }
            },
        }

        webhook = RazorpayWebhookNormalizer.normalize(raw_payload=payload)
        assert webhook.event == "payment.authorized"
        assert webhook.payment_id == "pay_authorizedABC"
        assert webhook.amount == 1000.0


# ---------------------------------------------------------------------------
# Test 22: Webhook Normalization — Hard Decline
# ---------------------------------------------------------------------------

class TestWebhookNormalizationHardDecline:
    def test_card_blocked_maps_to_hard_hardness(self):
        from gateway.razorpay_webhook import RazorpayWebhookNormalizer

        payload = {
            "event": "payment.failed",
            "entity": "event",
            "contains": ["payment"],
            "payload": {
                "payment": {
                    "entity": {
                        "id": "pay_hardXYZ",
                        "amount": 50000,
                        "currency": "INR",
                        "status": "failed",
                        "captured": False,
                        "error_code": "CARD_BLOCKED",
                    }
                }
            },
        }

        webhook = RazorpayWebhookNormalizer.normalize(raw_payload=payload)
        assert webhook.hardness == "hard"


# ---------------------------------------------------------------------------
# Test 23: Webhook Normalization — order.paid
# ---------------------------------------------------------------------------

class TestWebhookNormalizationOrderPaid:
    def test_order_paid_maps_to_captured(self):
        from gateway.razorpay_webhook import RazorpayWebhookNormalizer

        payload = {
            "event": "order.paid",
            "entity": "event",
            "contains": ["order"],
            "payload": {
                "order": {
                    "entity": {
                        "id": "order_paidXYZ",
                        "amount": 100000,
                        "currency": "INR",
                        "status": "paid",
                        "attempts": 1,
                    }
                }
            },
        }

        webhook = RazorpayWebhookNormalizer.normalize(raw_payload=payload)
        assert webhook.event == "payment.captured"  # order.paid → captured


# ---------------------------------------------------------------------------
# Test 24: Webhook Normalization — Metadata Untrusted
# ---------------------------------------------------------------------------

class TestWebhookUntrustedMetadata:
    def test_notes_marked_untrusted(self):
        from gateway.razorpay_webhook import RazorpayWebhookNormalizer

        payload = {
            "event": "payment.failed",
            "entity": "event",
            "contains": ["payment"],
            "payload": {
                "payment": {
                    "entity": {
                        "id": "pay_injectionTest",
                        "amount": 1000,
                        "currency": "INR",
                        "status": "failed",
                        "captured": False,
                        "notes": {
                            "injected_field": "OVERRIDE_RECOVERY_DECISION",
                            "fake_state": "VERIFIED_RECOVERY",
                        },
                    }
                }
            },
        }

        webhook = RazorpayWebhookNormalizer.normalize(raw_payload=payload)
        # Notes should not influence event normalization
        assert webhook.event == "payment.failed"
        # UNTRUSTED annotation must be present
        assert "UNTRUSTED_notes" in webhook.payload


# ---------------------------------------------------------------------------
# Test 25: Adapter — Simulation Mode Payment Link
# ---------------------------------------------------------------------------

class TestAdapterSimulationPaymentLink:
    def test_simulation_payment_link_no_http(self, monkeypatch):
        monkeypatch.setenv("RECOVERAI_PROVIDER_MODE", "simulation")
        from gateway.razorpay_adapter import RazorpayGatewayAdapter
        from gateway.provider_config import ProviderMode
        from gateway.models import GatewayActionStatus

        adapter = RazorpayGatewayAdapter(mode=ProviderMode.SIMULATION)
        result = adapter.create_payment_link(
            payment_id="pay_sim001",
            amount=500.0,
        )
        assert result.simulation is True
        assert result.status == GatewayActionStatus.SUCCESS
        assert result.provider == "razorpay"
        assert "SIMULATION" in result.message


# ---------------------------------------------------------------------------
# Test 26: Provider Status Endpoint — Simulation Mode
# ---------------------------------------------------------------------------

class TestProviderStatusSimulation:
    def test_simulation_status_response(self, monkeypatch):
        monkeypatch.setenv("RECOVERAI_PROVIDER_MODE", "simulation")
        monkeypatch.delenv("RAZORPAY_KEY_ID", raising=False)
        monkeypatch.delenv("RAZORPAY_KEY_SECRET", raising=False)

        from gateway.provider_config import get_provider_mode, get_capabilities, ProviderMode
        mode = get_provider_mode()
        caps = get_capabilities(mode)

        assert mode == ProviderMode.SIMULATION
        assert caps.live_money_execution is False
        assert caps.verify_webhook_signature is False


# ---------------------------------------------------------------------------
# Test 27: Secret Redaction
# ---------------------------------------------------------------------------

class TestSecretRedaction:
    def test_key_secret_not_in_masked_key_id(self):
        from gateway.razorpay_client import RazorpayClient

        client = RazorpayClient(key_id="rzp_test_abcdef", key_secret="my_very_secret_key_12345")
        masked = client._masked_key_id()
        assert "my_very_secret_key_12345" not in masked
        assert "12345" not in masked

    def test_key_secret_not_in_str_representation(self):
        from gateway.razorpay_client import RazorpayClient

        client = RazorpayClient(key_id="rzp_test_abcdef", key_secret="ultra_secret_xyz")
        # String representation should not expose secret
        assert "ultra_secret_xyz" not in repr(client)
        assert "ultra_secret_xyz" not in str(client)


# ---------------------------------------------------------------------------
# Test 28: Test Connection — Simulation Mode
# ---------------------------------------------------------------------------

class TestConnectionSimulationMode:
    def test_simulation_connection_always_succeeds(self, monkeypatch):
        monkeypatch.setenv("RECOVERAI_PROVIDER_MODE", "simulation")
        from gateway.razorpay_adapter import RazorpayGatewayAdapter
        from gateway.provider_config import ProviderMode

        adapter = RazorpayGatewayAdapter(mode=ProviderMode.SIMULATION)
        success, message = adapter.test_connection()
        assert success is True
        assert "SIMULATION" in message
