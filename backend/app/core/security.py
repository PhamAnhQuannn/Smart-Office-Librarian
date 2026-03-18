"""FR-1 core security primitives.

Provides HS256 JWT verification, user role extraction, and RBAC filter
construction per DECISIONS.md §4-5 and REQUIREMENTS.md FR-1.1/FR-1.2/FR-1.3.
Includes FR-1.4 secret encryption-at-rest support using AES-256 (pure stdlib).
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import secrets
import time
from dataclasses import dataclass
from enum import Enum
from typing import Any


class UserRole(str, Enum):
    ADMIN = "admin"
    USER = "user"


@dataclass(frozen=True)
class AuthenticatedUser:
    user_id: str
    role: UserRole
    workspace_id: str = ""
    workspace_slug: str = ""

    @property
    def is_admin(self) -> bool:
        return self.role == UserRole.ADMIN


class AuthenticationError(Exception):
    """Raised on authentication failure (→ HTTP 401 UNAUTHENTICATED)."""

    error_code: str = "UNAUTHENTICATED"


class SecretEncryptionError(Exception):
    """Raised when an encrypted secret cannot be encrypted/decrypted safely."""


_AES_BLOCK_SIZE = 16
_AES_ROUNDS_256 = 14
_SECRET_PREFIX = "enc-v1:"
_SECRET_NONCE_BYTES = 12
_SECRET_MAC_BYTES = 32

# AES substitution box and round constants from FIPS-197.
_SBOX = [
    0x63, 0x7C, 0x77, 0x7B, 0xF2, 0x6B, 0x6F, 0xC5, 0x30, 0x01, 0x67, 0x2B, 0xFE, 0xD7, 0xAB, 0x76,
    0xCA, 0x82, 0xC9, 0x7D, 0xFA, 0x59, 0x47, 0xF0, 0xAD, 0xD4, 0xA2, 0xAF, 0x9C, 0xA4, 0x72, 0xC0,
    0xB7, 0xFD, 0x93, 0x26, 0x36, 0x3F, 0xF7, 0xCC, 0x34, 0xA5, 0xE5, 0xF1, 0x71, 0xD8, 0x31, 0x15,
    0x04, 0xC7, 0x23, 0xC3, 0x18, 0x96, 0x05, 0x9A, 0x07, 0x12, 0x80, 0xE2, 0xEB, 0x27, 0xB2, 0x75,
    0x09, 0x83, 0x2C, 0x1A, 0x1B, 0x6E, 0x5A, 0xA0, 0x52, 0x3B, 0xD6, 0xB3, 0x29, 0xE3, 0x2F, 0x84,
    0x53, 0xD1, 0x00, 0xED, 0x20, 0xFC, 0xB1, 0x5B, 0x6A, 0xCB, 0xBE, 0x39, 0x4A, 0x4C, 0x58, 0xCF,
    0xD0, 0xEF, 0xAA, 0xFB, 0x43, 0x4D, 0x33, 0x85, 0x45, 0xF9, 0x02, 0x7F, 0x50, 0x3C, 0x9F, 0xA8,
    0x51, 0xA3, 0x40, 0x8F, 0x92, 0x9D, 0x38, 0xF5, 0xBC, 0xB6, 0xDA, 0x21, 0x10, 0xFF, 0xF3, 0xD2,
    0xCD, 0x0C, 0x13, 0xEC, 0x5F, 0x97, 0x44, 0x17, 0xC4, 0xA7, 0x7E, 0x3D, 0x64, 0x5D, 0x19, 0x73,
    0x60, 0x81, 0x4F, 0xDC, 0x22, 0x2A, 0x90, 0x88, 0x46, 0xEE, 0xB8, 0x14, 0xDE, 0x5E, 0x0B, 0xDB,
    0xE0, 0x32, 0x3A, 0x0A, 0x49, 0x06, 0x24, 0x5C, 0xC2, 0xD3, 0xAC, 0x62, 0x91, 0x95, 0xE4, 0x79,
    0xE7, 0xC8, 0x37, 0x6D, 0x8D, 0xD5, 0x4E, 0xA9, 0x6C, 0x56, 0xF4, 0xEA, 0x65, 0x7A, 0xAE, 0x08,
    0xBA, 0x78, 0x25, 0x2E, 0x1C, 0xA6, 0xB4, 0xC6, 0xE8, 0xDD, 0x74, 0x1F, 0x4B, 0xBD, 0x8B, 0x8A,
    0x70, 0x3E, 0xB5, 0x66, 0x48, 0x03, 0xF6, 0x0E, 0x61, 0x35, 0x57, 0xB9, 0x86, 0xC1, 0x1D, 0x9E,
    0xE1, 0xF8, 0x98, 0x11, 0x69, 0xD9, 0x8E, 0x94, 0x9B, 0x1E, 0x87, 0xE9, 0xCE, 0x55, 0x28, 0xDF,
    0x8C, 0xA1, 0x89, 0x0D, 0xBF, 0xE6, 0x42, 0x68, 0x41, 0x99, 0x2D, 0x0F, 0xB0, 0x54, 0xBB, 0x16,
]
_RCON = [0x00, 0x01, 0x02, 0x04, 0x08, 0x10, 0x20, 0x40, 0x80, 0x1B, 0x36]


def _b64url_decode(data: str) -> bytes:
    padding = (4 - len(data) % 4) % 4
    return base64.urlsafe_b64decode(data + "=" * padding)


def _b64url_encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).decode().rstrip("=")


def _gf_mul(a: int, b: int) -> int:
    result = 0
    left = a
    right = b
    for _ in range(8):
        if right & 1:
            result ^= left
        high_bit = left & 0x80
        left = (left << 1) & 0xFF
        if high_bit:
            left ^= 0x1B
        right >>= 1
    return result


def _rot_word(word: list[int]) -> list[int]:
    return word[1:] + word[:1]


def _sub_word(word: list[int]) -> list[int]:
    return [_SBOX[value] for value in word]


def _expand_key_256(key: bytes) -> list[list[int]]:
    if len(key) != 32:
        raise SecretEncryptionError("AES-256 key must be exactly 32 bytes")

    nk = 8
    nb = 4
    nr = _AES_ROUNDS_256
    words: list[list[int]] = [list(key[index:index + 4]) for index in range(0, len(key), 4)]

    for index in range(nk, nb * (nr + 1)):
        temp = words[index - 1][:]
        if index % nk == 0:
            temp = _sub_word(_rot_word(temp))
            temp[0] ^= _RCON[index // nk]
        elif index % nk == 4:
            temp = _sub_word(temp)
        words.append([words[index - nk][offset] ^ temp[offset] for offset in range(4)])

    round_keys: list[list[int]] = []
    for round_index in range(nr + 1):
        key_block: list[int] = []
        for column in range(4):
            key_block.extend(words[round_index * 4 + column])
        round_keys.append(key_block)
    return round_keys


def _bytes_to_state(block: bytes) -> list[list[int]]:
    if len(block) != _AES_BLOCK_SIZE:
        raise SecretEncryptionError("AES block operations require 16-byte input")
    state = [[0 for _ in range(4)] for _ in range(4)]
    for index, value in enumerate(block):
        state[index % 4][index // 4] = value
    return state


def _state_to_bytes(state: list[list[int]]) -> bytes:
    output = bytearray(_AES_BLOCK_SIZE)
    for column in range(4):
        for row in range(4):
            output[column * 4 + row] = state[row][column]
    return bytes(output)


def _add_round_key(state: list[list[int]], round_key: list[int]) -> None:
    for column in range(4):
        for row in range(4):
            state[row][column] ^= round_key[column * 4 + row]


def _sub_bytes(state: list[list[int]]) -> None:
    for row in range(4):
        for column in range(4):
            state[row][column] = _SBOX[state[row][column]]


def _shift_rows(state: list[list[int]]) -> None:
    for row in range(1, 4):
        state[row] = state[row][row:] + state[row][:row]


def _mix_columns(state: list[list[int]]) -> None:
    for column in range(4):
        a0, a1, a2, a3 = [state[row][column] for row in range(4)]
        state[0][column] = _gf_mul(a0, 2) ^ _gf_mul(a1, 3) ^ a2 ^ a3
        state[1][column] = a0 ^ _gf_mul(a1, 2) ^ _gf_mul(a2, 3) ^ a3
        state[2][column] = a0 ^ a1 ^ _gf_mul(a2, 2) ^ _gf_mul(a3, 3)
        state[3][column] = _gf_mul(a0, 3) ^ a1 ^ a2 ^ _gf_mul(a3, 2)


def _aes256_encrypt_block(block: bytes, round_keys: list[list[int]]) -> bytes:
    state = _bytes_to_state(block)
    _add_round_key(state, round_keys[0])

    for round_index in range(1, _AES_ROUNDS_256):
        _sub_bytes(state)
        _shift_rows(state)
        _mix_columns(state)
        _add_round_key(state, round_keys[round_index])

    _sub_bytes(state)
    _shift_rows(state)
    _add_round_key(state, round_keys[_AES_ROUNDS_256])
    return _state_to_bytes(state)


def _derive_key_material(key_material: str) -> tuple[bytes, bytes]:
    normalized = key_material.strip() if key_material else ""
    if not normalized:
        raise SecretEncryptionError("Missing secret-encryption key material")

    try:
        if normalized.startswith("hex:"):
            seed_input = bytes.fromhex(normalized[len("hex:"):])
        elif normalized.startswith("base64:"):
            seed_input = _b64url_decode(normalized[len("base64:"):])
        else:
            seed_input = normalized.encode()
    except Exception as exc:
        raise SecretEncryptionError("Invalid secret-encryption key material format") from exc

    seed = hashlib.sha256(seed_input).digest()
    encryption_key = hashlib.sha256(seed + b":aes256").digest()
    mac_key = hashlib.sha256(seed + b":hmac256").digest()
    return encryption_key, mac_key


def _aes256_ctr_transform(data: bytes, *, key: bytes, nonce: bytes) -> bytes:
    if len(nonce) != _SECRET_NONCE_BYTES:
        raise SecretEncryptionError("Invalid nonce length for AES-256-CTR")

    round_keys = _expand_key_256(key)
    output = bytearray(len(data))

    counter = 0
    offset = 0
    while offset < len(data):
        counter_block = nonce + counter.to_bytes(4, "big")
        keystream = _aes256_encrypt_block(counter_block, round_keys)
        chunk = data[offset:offset + _AES_BLOCK_SIZE]
        for index, value in enumerate(chunk):
            output[offset + index] = value ^ keystream[index]
        offset += len(chunk)
        counter += 1
        if counter > 0xFFFFFFFF:
            raise SecretEncryptionError("Secret value is too large for AES-CTR counter space")

    return bytes(output)


def is_encrypted_secret_value(value: str) -> bool:
    return isinstance(value, str) and value.startswith(_SECRET_PREFIX)


def encrypt_secret_value(secret_value: str, *, key_material: str) -> str:
    """Encrypt a secret for storage using AES-256-CTR + HMAC-SHA256 integrity."""
    if not isinstance(secret_value, str):
        raise SecretEncryptionError("Secret value must be a string")

    encryption_key, mac_key = _derive_key_material(key_material)
    nonce = secrets.token_bytes(_SECRET_NONCE_BYTES)
    plaintext = secret_value.encode("utf-8")
    ciphertext = _aes256_ctr_transform(plaintext, key=encryption_key, nonce=nonce)

    payload = nonce + ciphertext
    mac = hmac.new(mac_key, payload, hashlib.sha256).digest()
    return _SECRET_PREFIX + _b64url_encode(payload + mac)


def decrypt_secret_value(encrypted_value: str, *, key_material: str) -> str:
    """Decrypt an encrypted secret value previously produced by encrypt_secret_value."""
    if not is_encrypted_secret_value(encrypted_value):
        raise SecretEncryptionError("Encrypted secret value is missing required prefix")

    encoded_payload = encrypted_value[len(_SECRET_PREFIX):]
    try:
        blob = _b64url_decode(encoded_payload)
    except Exception as exc:
        raise SecretEncryptionError("Encrypted secret payload is not valid base64") from exc

    if len(blob) < (_SECRET_NONCE_BYTES + _SECRET_MAC_BYTES):
        raise SecretEncryptionError("Encrypted secret payload is malformed")

    payload = blob[:-_SECRET_MAC_BYTES]
    received_mac = blob[-_SECRET_MAC_BYTES:]
    nonce = payload[:_SECRET_NONCE_BYTES]
    ciphertext = payload[_SECRET_NONCE_BYTES:]

    encryption_key, mac_key = _derive_key_material(key_material)
    expected_mac = hmac.new(mac_key, payload, hashlib.sha256).digest()
    if not hmac.compare_digest(expected_mac, received_mac):
        raise SecretEncryptionError("Encrypted secret authentication failed")

    plaintext = _aes256_ctr_transform(ciphertext, key=encryption_key, nonce=nonce)
    try:
        return plaintext.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise SecretEncryptionError("Encrypted secret payload could not be decoded") from exc


def decode_jwt_token(token: str, *, secret: str) -> dict[str, Any]:
    """Verify an HS256 JWT and return its payload claims.

    Raises AuthenticationError on invalid signature, expiry, or malformed input.
    """
    try:
        parts = token.split(".")
        if len(parts) != 3:
            raise AuthenticationError("Malformed JWT: expected 3 dot-separated parts")

        header_b64, payload_b64, signature_b64 = parts

        signing_input = f"{header_b64}.{payload_b64}".encode()
        expected_sig = hmac.new(
            secret.encode(),
            signing_input,
            hashlib.sha256,
        ).digest()
        received_sig = _b64url_decode(signature_b64)

        if not hmac.compare_digest(expected_sig, received_sig):
            raise AuthenticationError("JWT signature verification failed")

        payload: dict[str, Any] = json.loads(_b64url_decode(payload_b64).decode())

        exp = payload.get("exp")
        if exp is not None and exp < time.time():
            raise AuthenticationError("JWT has expired")

        return payload

    except AuthenticationError:
        raise
    except Exception as exc:
        raise AuthenticationError("JWT decode error") from exc


def issue_jwt_token(
    *,
    user_id: str,
    email: str,
    role: str,
    secret: str,
    workspace_id: str = "",
    workspace_slug: str = "",
    expires_in_seconds: int = 86400,
) -> str:
    """Issue a signed HS256 JWT for the given user.

    Produces a token compatible with decode_jwt_token and the frontend AuthUser type.
    """
    header = _b64url_encode(
        json.dumps({"alg": "HS256", "typ": "JWT"}, separators=(",", ":")).encode()
    )
    payload_data: dict[str, Any] = {
        "sub": user_id,
        "email": email,
        "role": role,
        "workspace_id": workspace_id,
        "workspace_slug": workspace_slug,
        "exp": int(time.time()) + expires_in_seconds,
    }
    payload = _b64url_encode(
        json.dumps(payload_data, separators=(",", ":")).encode()
    )
    signing_input = f"{header}.{payload}".encode()
    sig = hmac.new(secret.encode(), signing_input, hashlib.sha256).digest()
    signature = _b64url_encode(sig)
    return f"{header}.{payload}.{signature}"


def build_rbac_filter(user: AuthenticatedUser) -> dict[str, Any]:
    """Return the canonical Pinecone RBAC metadata filter (DECISIONS.md §5.1).

    Semantics: (visibility == \"public\") OR (allowed_user_ids $in [user_id])
    """
    return {
        "$or": [
            {"visibility": {"$eq": "public"}},
            {"allowed_user_ids": {"$in": [user.user_id]}},
        ]
    }
