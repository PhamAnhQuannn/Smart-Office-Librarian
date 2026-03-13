from __future__ import annotations

import base64

import pytest

from app.core.security import (
    SecretEncryptionError,
    decrypt_secret_value,
    encrypt_secret_value,
    is_encrypted_secret_value,
)


def test_secrets_encryption_round_trip_returns_original_secret() -> None:
    encrypted = encrypt_secret_value("github-token-123", key_material="master-key")
    decrypted = decrypt_secret_value(encrypted, key_material="master-key")

    assert decrypted == "github-token-123"


def test_secrets_encryption_output_is_tagged_and_not_plaintext() -> None:
    secret = "super-secret-value"
    encrypted = encrypt_secret_value(secret, key_material="master-key")

    assert is_encrypted_secret_value(encrypted)
    assert secret not in encrypted


def test_secrets_encryption_detects_payload_tampering() -> None:
    encrypted = encrypt_secret_value("secret-to-protect", key_material="master-key")
    encoded_payload = encrypted.split(":", maxsplit=1)[1]
    padding = "=" * ((4 - len(encoded_payload) % 4) % 4)
    blob = bytearray(base64.urlsafe_b64decode(encoded_payload + padding))
    blob[len(blob) // 2] ^= 0x01
    tampered_payload = base64.urlsafe_b64encode(bytes(blob)).decode().rstrip("=")
    tampered = "enc-v1:" + tampered_payload

    with pytest.raises(SecretEncryptionError, match="authentication failed"):
        decrypt_secret_value(tampered, key_material="master-key")


def test_secrets_encryption_fails_with_wrong_key() -> None:
    encrypted = encrypt_secret_value("secret-to-protect", key_material="master-key")

    with pytest.raises(SecretEncryptionError, match="authentication failed"):
        decrypt_secret_value(encrypted, key_material="wrong-master-key")


def test_secrets_encryption_accepts_hex_and_base64_key_formats() -> None:
    encrypted_hex = encrypt_secret_value("hex-secret", key_material="hex:00112233445566778899aabbccddeeff")
    assert decrypt_secret_value(encrypted_hex, key_material="hex:00112233445566778899aabbccddeeff") == "hex-secret"

    encrypted_b64 = encrypt_secret_value("b64-secret", key_material="base64:c2VjcmV0LWtleS1tYXRlcmlhbA")
    assert decrypt_secret_value(encrypted_b64, key_material="base64:c2VjcmV0LWtleS1tYXRlcmlhbA") == "b64-secret"


def test_secrets_encryption_rejects_unencrypted_payload() -> None:
    with pytest.raises(SecretEncryptionError, match="missing required prefix"):
        decrypt_secret_value("plain-secret", key_material="master-key")
