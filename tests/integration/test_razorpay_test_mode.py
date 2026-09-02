"""
Razorpay Test Mode Integration Tests — Step 14.

These tests make REAL Razorpay Test API calls.
They are SKIPPED if RAZORPAY_KEY_ID is not configured in environment.

To run:
  export RAZORPAY_KEY_ID=rzp_test_your_key
  export RAZORPAY_KEY_SECRET=your_secret
  export RAZORPAY_WEBHOOK_SECRET=your_webhook_secret
  pytest tests/integration/test_razorpay_test_mode.py -v -m razorpay_integration

All tests use Razorpay TEST Mode keys — no real money.
"""

import sys
import os
import hmac
import hashlib
from pathlib import Path
import pytest

# Add src to Python path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))



RAZORPAY_KEY_ID = os.getenv("RAZORPAY_KEY_ID", "")
RAZORPAY_KEY_SECRET = os.getenv("RAZORPAY_KEY_SECRET", "")
RAZORPAY_WEBHOOK_SECRET = os.getenv("RAZORPAY_WEBHOOK_SECRET", "")

requires_razorpay = pytest.mark.skipif(
    not RAZORPAY_KEY_ID or not RAZORPAY_KEY_SECRET,
    reason="RAZORPAY_KEY_ID and RAZORPAY_KEY_SECRET not set — skipping live integration tests",
)


@pytest.mark.razorpay_integration
@requires_razorpay
class TestRazorpayTestModeConnectivity:
    """Real connectivity tests against Razorpay Test API."""

    def test_connection_succeeds_with_valid_keys(self):
        """Test that Razorpay Test API is reachable with configured credentials."""
        from gateway.razorpay_client import RazorpayClient
        client = RazorpayClient()
        success, message = client.test_connection()
        assert success is True, f"Connection failed: {message}"
        print(f"\n[INTEGRATION] Razorpay Test API connectivity: {message}")

    def test_invalid_payment_id_returns_404(self):
        """Fetching a non-existent payment returns NotFoundError."""
        from gateway.razorpay_client import RazorpayClient, RazorpayNotFoundError
        client = RazorpayClient()
        with pytest.raises(RazorpayNotFoundError):
            client.fetch_payment("pay_THIS_DOES_NOT_EXIST_xyz123")


@pytest.mark.razorpay_integration
@requires_razorpay
class TestRazorpayPaymentLinkCreation:
    """Test real payment link creation in Razorpay Test Mode."""

    def test_create_payment_link_real(self):
        """Create a real Razorpay Test Mode payment link."""
        from gateway.razorpay_client import RazorpayClient
        from gateway.razorpay_models import RazorpayPaymentLinkRequest
        import uuid

        client = RazorpayClient()
        ref_id = f"recoverai_test_{uuid.uuid4().hex[:8]}"

        request = RazorpayPaymentLinkRequest(
            amount=100,  # ₹1 — minimum test amount
            currency="INR",
            description="RecoverAI Step 14 Integration Test",
            reference_id=ref_id,
        )

        link = client.create_payment_link(request)
        assert link.id is not None
        assert link.id.startswith("plink_")
        assert link.amount == 100
        assert link.currency == "INR"
        assert link.is_active is True
        print(f"\n[INTEGRATION] Created payment link: {link.id} → {link.short_url}")


@pytest.mark.razorpay_integration
@requires_razorpay
class TestRazorpayAdapterTestMode:
    """Test Razorpay adapter in TEST mode with real API."""

    def test_adapter_test_mode_connection(self):
        """Adapter test connection in RAZORPAY_TEST mode."""
        from gateway.razorpay_adapter import RazorpayGatewayAdapter
        from gateway.provider_config import ProviderMode

        adapter = RazorpayGatewayAdapter(mode=ProviderMode.RAZORPAY_TEST)
        assert adapter.is_simulation is False
        assert adapter.provider_mode == ProviderMode.RAZORPAY_TEST

        success, message = adapter.test_connection()
        assert success is True, f"Adapter connection failed: {message}"

    def test_adapter_payment_link_creation(self):
        """Adapter creates real payment link in TEST mode."""
        from gateway.razorpay_adapter import RazorpayGatewayAdapter
        from gateway.provider_config import ProviderMode
        from gateway.models import GatewayActionStatus
        import uuid

        adapter = RazorpayGatewayAdapter(mode=ProviderMode.RAZORPAY_TEST)
        payment_id = f"test_pay_{uuid.uuid4().hex[:8]}"

        result = adapter.create_payment_link(
            payment_id=payment_id,
            amount=1.0,  # ₹1
            description="RecoverAI integration test",
        )

        assert result.status == GatewayActionStatus.SUCCESS
        assert result.simulation is False
        assert result.provider == "razorpay"
        assert "RAZORPAY TEST" in result.message
        assert result.metadata.get("provider_mode") == "razorpay_test"
        assert result.metadata.get("live_money") is False
        print(f"\n[INTEGRATION] Payment link via adapter: {result.message}")


@pytest.mark.razorpay_integration
@requires_razorpay
class TestRazorpayWebhookNormalizer:
    """Test webhook normalizer with realistic Razorpay event structure."""

    def test_normalize_real_payment_failed_structure(self):
        """Normalize a payment.failed event matching real Razorpay structure."""
        from gateway.razorpay_webhook import RazorpayWebhookNormalizer

        real_razorpay_payload = {
            "entity": "event",
            "account_id": "acc_TEST123",
            "event": "payment.failed",
            "contains": ["payment"],
            "payload": {
                "payment": {
                    "entity": {
                        "id": "pay_realtest001",
                        "entity": "payment",
                        "amount": 50000,
                        "currency": "INR",
                        "status": "failed",
                        "order_id": "order_realtest001",
                        "method": "upi",
                        "error_code": "BAD_REQUEST_ERROR",
                        "error_description": "VPA not registered",
                        "error_source": "customer",
                        "error_step": "payment_authentication",
                        "error_reason": "invalid_vpa",
                        "captured": False,
                    }
                }
            },
            "created_at": 1735689600,
        }

        webhook = RazorpayWebhookNormalizer.normalize(
            raw_payload=real_razorpay_payload,
            provider_event_id="evt_realtest001",
            signature_verified=True,
        )

        assert webhook.event == "payment.failed"
        assert webhook.payment_id == "pay_realtest001"
        assert webhook.order_id == "order_realtest001"
        assert webhook.amount == 500.0
        assert webhook.method == "upi"
        assert webhook.provider == "razorpay"
        assert webhook.payload["signature_verified"] is True
        assert webhook.payload["provider"] == "razorpay"

    def test_webhook_signature_with_real_secret(self):
        """Validate HMAC-SHA256 webhook signature matches Razorpay algorithm."""
        if not RAZORPAY_WEBHOOK_SECRET:
            pytest.skip("RAZORPAY_WEBHOOK_SECRET not set")

        from gateway.razorpay_webhook import RazorpayWebhookSignatureValidator

        body = b'{"event":"payment.captured","id":"test_evt_001"}'
        expected_sig = hmac.new(
            RAZORPAY_WEBHOOK_SECRET.encode("utf-8"),
            body,
            hashlib.sha256,
        ).hexdigest()

        result = RazorpayWebhookSignatureValidator.validate(
            raw_body=body,
            signature=expected_sig,
            webhook_secret=RAZORPAY_WEBHOOK_SECRET,
        )
        assert result is True

    def test_provider_http200_is_not_verified_recovery(self):
        """
        CRITICAL: Razorpay returning HTTP 200 with status=authorized
        must NOT be treated as VERIFIED_RECOVERY in RecoverAI.
        This test validates that the normalizer does not set verified state.
        """
        from gateway.razorpay_webhook import RazorpayWebhookNormalizer

        payload = {
            "event": "payment.authorized",
            "entity": "event",
            "contains": ["payment"],
            "payload": {
                "payment": {
                    "entity": {
                        "id": "pay_authorized001",
                        "amount": 100000,
                        "currency": "INR",
                        "status": "authorized",
                        "captured": False,
                        "method": "card",
                    }
                }
            },
        }

        webhook = RazorpayWebhookNormalizer.normalize(raw_payload=payload)

        # The webhook event says "authorized" — this is NOT a verified recovery
        # RecoveryVerifier performs independent ledger evaluation
        assert webhook.event == "payment.authorized"
        # The payload must NOT include any field claiming "verified_recovery"
        payload_data = webhook.payload
        assert "verified_recovery" not in str(payload_data).lower() or payload_data.get("verified_recovery", False) is False
