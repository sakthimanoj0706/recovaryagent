"""
Razorpay HTTP Client for RecoverAI.

Performs real HTTP calls to the Razorpay Test API using HTTP Basic Authentication.
Designed for RAZORPAY_TEST mode only. Live mode is hard-blocked.

Security Principles:
- key_secret is NEVER logged, printed, or included in error messages
- Authorization header is NEVER logged
- Correlation IDs propagate through every request
- Conservative retry: only on safe READ operations
- No blind retry on state-changing operations (create, capture)
"""

import os
import json
import hmac
import hashlib
import logging
import time
import uuid
from base64 import b64encode
from datetime import datetime, timezone
from typing import Optional, List, Tuple, Dict, Any
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError
from urllib.parse import urljoin

from .razorpay_models import (
    RazorpayPayment,
    RazorpayOrder,
    RazorpayOrderPayments,
    RazorpayPaymentLink,
    RazorpayPaymentLinkRequest,
    RazorpayError,
)

logger = logging.getLogger(__name__)

# Default Razorpay v1 API base URL
RAZORPAY_BASE_URL = "https://api.razorpay.com/v1/"

# Timeouts
DEFAULT_TIMEOUT_SECONDS = 15
MAX_RETRIES_READ = 2
RETRY_DELAY_SECONDS = 1.0


class RazorpayClientError(Exception):
    """Base error from Razorpay client."""

    def __init__(self, message: str, status_code: Optional[int] = None, error_code: Optional[str] = None):
        super().__init__(message)
        self.status_code = status_code
        self.error_code = error_code


class RazorpayAuthError(RazorpayClientError):
    """Authentication failure (HTTP 401/403)."""
    pass


class RazorpayNotFoundError(RazorpayClientError):
    """Resource not found (HTTP 404)."""
    pass


class RazorpayRateLimitError(RazorpayClientError):
    """Rate limit exceeded (HTTP 429)."""
    pass


class RazorpayServerError(RazorpayClientError):
    """Razorpay server error (HTTP 5xx)."""
    pass


class RazorpayTimeoutError(RazorpayClientError):
    """Request timed out."""
    pass


class RazorpayMalformedResponseError(RazorpayClientError):
    """Response could not be parsed as valid JSON."""
    pass


class RazorpayClient:
    """
    Minimal, safe HTTP client for the Razorpay REST API.

    Only implements the operations actually needed by the RecoverAI recovery workflow:
      - fetch_payment(payment_id)
      - fetch_order(order_id)
      - fetch_order_payments(order_id)
      - create_payment_link(request)
      - test_connection()

    Authentication: HTTP Basic (key_id as username, key_secret as password).
    The key_secret is NEVER logged or exposed.
    """

    def __init__(
        self,
        key_id: Optional[str] = None,
        key_secret: Optional[str] = None,
        base_url: Optional[str] = None,
        timeout: float = DEFAULT_TIMEOUT_SECONDS,
    ):
        self._key_id = key_id or os.getenv("RAZORPAY_KEY_ID", "")
        self._key_secret = key_secret or os.getenv("RAZORPAY_KEY_SECRET", "")
        self._base_url = (base_url or os.getenv("RAZORPAY_BASE_URL", RAZORPAY_BASE_URL)).rstrip("/") + "/"
        self._timeout = timeout

        if not self._key_id or not self._key_secret:
            raise RazorpayClientError(
                "Razorpay credentials not configured. "
                "Set RAZORPAY_KEY_ID and RAZORPAY_KEY_SECRET environment variables. "
                "Use Test Mode keys only (prefix: rzp_test_)."
            )

    def _masked_key_id(self) -> str:
        """Return partially masked key_id for safe logging."""
        kid = self._key_id
        if len(kid) > 10:
            return kid[:8] + "***"
        return "***"

    def _auth_header(self) -> str:
        """Build HTTP Basic Auth header. Never logged."""
        credentials = f"{self._key_id}:{self._key_secret}"
        encoded = b64encode(credentials.encode("utf-8")).decode("ascii")
        return f"Basic {encoded}"

    def _request(
        self,
        method: str,
        path: str,
        body: Optional[Dict[str, Any]] = None,
        correlation_id: Optional[str] = None,
        retry: bool = False,
    ) -> Dict[str, Any]:
        """
        Execute an HTTP request to the Razorpay API.

        Args:
            method: HTTP method (GET, POST)
            path: URL path relative to base URL
            body: Optional JSON request body
            correlation_id: RecoverAI correlation ID for tracing
            retry: Whether safe retry is allowed (READ-only operations)

        Returns:
            Parsed JSON response dict

        Raises:
            RazorpayAuthError, RazorpayNotFoundError, RazorpayRateLimitError,
            RazorpayServerError, RazorpayTimeoutError, RazorpayMalformedResponseError,
            RazorpayClientError
        """
        url = urljoin(self._base_url, path.lstrip("/"))
        cid = correlation_id or f"cid_{uuid.uuid4().hex[:10]}"
        attempts = (MAX_RETRIES_READ + 1) if retry else 1

        last_error: Optional[Exception] = None

        for attempt in range(1, attempts + 1):
            start_ms = int(time.monotonic() * 1000)
            try:
                headers = {
                    "Authorization": self._auth_header(),  # NEVER logged
                    "Content-Type": "application/json",
                    "Accept": "application/json",
                    "X-Correlation-ID": cid,
                }

                data = json.dumps(body).encode("utf-8") if body else None
                req = Request(url, data=data, headers=headers, method=method)

                with urlopen(req, timeout=self._timeout) as resp:
                    raw = resp.read()
                    duration_ms = int(time.monotonic() * 1000) - start_ms

                    logger.info(
                        "Razorpay API request completed",
                        extra={
                            "correlation_id": cid,
                            "provider": "razorpay",
                            "mode": "test",
                            "operation": path,
                            "method": method,
                            "status_code": resp.status,
                            "duration_ms": duration_ms,
                            "success": True,
                            "attempt": attempt,
                            # key_id masked — key_secret NEVER included
                            "key_id": self._masked_key_id(),
                        },
                    )

                    try:
                        return json.loads(raw.decode("utf-8"))
                    except json.JSONDecodeError as exc:
                        raise RazorpayMalformedResponseError(
                            f"Razorpay returned non-JSON response for {method} {path}",
                            status_code=resp.status,
                        ) from exc

            except HTTPError as exc:
                duration_ms = int(time.monotonic() * 1000) - start_ms
                status_code = exc.code
                try:
                    error_body = json.loads(exc.read().decode("utf-8"))
                    razorpay_err = RazorpayError(**error_body)
                    err_desc = razorpay_err.get_description()
                    err_code = razorpay_err.get_code()
                except Exception:
                    err_desc = str(exc.reason or exc)
                    err_code = None

                logger.warning(
                    "Razorpay API error",
                    extra={
                        "correlation_id": cid,
                        "provider": "razorpay",
                        "operation": path,
                        "method": method,
                        "status_code": status_code,
                        "duration_ms": duration_ms,
                        "error_code": err_code,
                        "attempt": attempt,
                        # NEVER log key_secret, Authorization header, or err_desc verbatim
                        # as it could contain sensitive context
                    },
                )

                if status_code in (401, 403):
                    raise RazorpayAuthError(
                        f"Razorpay authentication failed ({status_code}). "
                        f"Check RAZORPAY_KEY_ID and RAZORPAY_KEY_SECRET. "
                        f"Ensure you are using Test Mode keys (prefix: rzp_test_).",
                        status_code=status_code,
                        error_code=err_code,
                    )
                elif status_code == 404:
                    raise RazorpayNotFoundError(
                        f"Razorpay resource not found: {path}",
                        status_code=404,
                        error_code=err_code,
                    )
                elif status_code == 429:
                    raise RazorpayRateLimitError(
                        "Razorpay rate limit exceeded. Please retry after a short delay.",
                        status_code=429,
                        error_code=err_code,
                    )
                elif status_code == 400:
                    raise RazorpayClientError(
                        f"Razorpay validation error ({status_code}): {err_desc}",
                        status_code=400,
                        error_code=err_code,
                    )
                elif status_code >= 500:
                    last_error = RazorpayServerError(
                        f"Razorpay server error ({status_code}). Provider may be temporarily unavailable.",
                        status_code=status_code,
                        error_code=err_code,
                    )
                    if retry and attempt < attempts:
                        time.sleep(RETRY_DELAY_SECONDS * attempt)
                        continue
                    raise last_error
                else:
                    raise RazorpayClientError(
                        f"Razorpay HTTP error ({status_code}): {err_desc}",
                        status_code=status_code,
                        error_code=err_code,
                    )

            except URLError as exc:
                duration_ms = int(time.monotonic() * 1000) - start_ms
                reason = str(exc.reason) if hasattr(exc, "reason") else str(exc)
                if "timed out" in reason.lower() or "timeout" in reason.lower():
                    last_error = RazorpayTimeoutError(
                        f"Razorpay API request timed out after {self._timeout}s. Path: {path}",
                    )
                else:
                    last_error = RazorpayClientError(
                        f"Razorpay connection error: {reason}",
                    )
                if retry and attempt < attempts:
                    time.sleep(RETRY_DELAY_SECONDS * attempt)
                    continue
                raise last_error

        raise last_error or RazorpayClientError("Unknown error communicating with Razorpay API")

    # ---------------------------------------------------------------------------
    # PUBLIC API METHODS
    # ---------------------------------------------------------------------------

    def test_connection(self, correlation_id: Optional[str] = None) -> Tuple[bool, str]:
        """
        Test connectivity to Razorpay API using the configured credentials.
        Returns (success, message).
        """
        try:
            # Fetch an order list with limit=1 — safe, non-destructive, idempotent
            self._request("GET", "orders?count=1", correlation_id=correlation_id, retry=True)
            return True, f"Razorpay Test API connected successfully (key: {self._masked_key_id()})"
        except RazorpayAuthError as exc:
            return False, f"Authentication failed — check credentials: {exc}"
        except RazorpayTimeoutError:
            return False, "Razorpay API timed out — check network connectivity"
        except RazorpayClientError as exc:
            return False, f"Razorpay API error: {exc}"

    def fetch_payment(
        self,
        payment_id: str,
        correlation_id: Optional[str] = None,
    ) -> RazorpayPayment:
        """
        Fetch payment details from Razorpay.
        Safe read operation — retried on transient errors.
        """
        data = self._request(
            "GET",
            f"payments/{payment_id}",
            correlation_id=correlation_id,
            retry=True,
        )
        return RazorpayPayment(**data)

    def fetch_order(
        self,
        order_id: str,
        correlation_id: Optional[str] = None,
    ) -> RazorpayOrder:
        """
        Fetch order details from Razorpay.
        Safe read operation — retried on transient errors.
        """
        data = self._request(
            "GET",
            f"orders/{order_id}",
            correlation_id=correlation_id,
            retry=True,
        )
        return RazorpayOrder(**data)

    def fetch_order_payments(
        self,
        order_id: str,
        correlation_id: Optional[str] = None,
    ) -> RazorpayOrderPayments:
        """
        Fetch all payments associated with an order.
        Safe read operation — retried on transient errors.
        """
        data = self._request(
            "GET",
            f"orders/{order_id}/payments",
            correlation_id=correlation_id,
            retry=True,
        )
        return RazorpayOrderPayments(**data)

    def create_payment_link(
        self,
        request: RazorpayPaymentLinkRequest,
        correlation_id: Optional[str] = None,
    ) -> RazorpayPaymentLink:
        """
        Create a Razorpay Payment Link.

        IMPORTANT: This is a state-changing operation.
        It is NOT automatically retried to avoid duplicate link creation.
        The caller must handle idempotency using reference_id.
        """
        body = {
            "amount": request.amount,
            "currency": request.currency,
            "notify": request.notify,
            "reminder_enable": request.reminder_enable,
        }
        if request.description:
            body["description"] = request.description
        if request.reference_id:
            body["reference_id"] = request.reference_id
        if request.expire_by:
            body["expire_by"] = request.expire_by
        if request.notes:
            body["notes"] = request.notes

        data = self._request(
            "POST",
            "payment_links",
            body=body,
            correlation_id=correlation_id,
            retry=False,  # DO NOT retry state-changing operations
        )
        return RazorpayPaymentLink(**data)


__all__ = [
    "RazorpayClient",
    "RazorpayClientError",
    "RazorpayAuthError",
    "RazorpayNotFoundError",
    "RazorpayRateLimitError",
    "RazorpayServerError",
    "RazorpayTimeoutError",
    "RazorpayMalformedResponseError",
]
