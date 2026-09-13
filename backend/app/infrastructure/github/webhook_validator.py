"""
Cryptographic validator for GitHub webhook HMAC-SHA256 signatures.
"""

import hashlib
import hmac

from app.domain.exceptions import WebhookValidationError


class GitHubWebhookValidator:
    """
    Validates that incoming webhook HTTP requests originate from GitHub
    by verifying the HMAC-SHA256 signature in the X-Hub-Signature-256 header.
    """

    SIGNATURE_PREFIX = "sha256="

    @classmethod
    def verify_signature(
        cls,
        payload_bytes: bytes,
        signature_header: str | None,
        secret: str,
    ) -> None:
        """
        Verify the HMAC-SHA256 signature against the raw payload bytes.

        Raises:
            WebhookValidationError: If header is missing, malformed, or signature mismatches.
        """
        if not signature_header:
            raise WebhookValidationError("Missing 'X-Hub-Signature-256' header.")

        if not signature_header.startswith(cls.SIGNATURE_PREFIX):
            raise WebhookValidationError(
                f"Invalid signature format. Expected prefix '{cls.SIGNATURE_PREFIX}'."
            )

        received_signature = signature_header[len(cls.SIGNATURE_PREFIX) :]

        # Compute HMAC-SHA256 using the shared secret
        mac = hmac.new(
            key=secret.encode("utf-8"),
            msg=payload_bytes,
            digestmod=hashlib.sha256,
        )
        expected_signature = mac.hexdigest()

        # Constant-time comparison to protect against timing attacks
        if not hmac.compare_digest(expected_signature, received_signature):
            raise WebhookValidationError(
                "Webhook HMAC signature verification failed. Untrusted payload."
            )
