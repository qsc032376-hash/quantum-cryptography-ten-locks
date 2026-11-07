"""Tier 1 classical helper: 24-bit key conversion and repeating-XOR decryption.

The quantum side recovers the hidden string as an integer ``s`` where bit ``j``
(value ``2**j``) is the parity on qubit ``j``.  Tier 1 masks its plaintext with
the three bytes ``s.to_bytes(3, "big")``, repeated (see ``tier01/README.md``).

This module only performs the classical data handling; it builds no circuits and
runs no simulations.  The XOR itself is delegated to
:func:`common.crypto.xor_repeating` so the official implementation stays the
single source of truth.
"""

from common.crypto import xor_repeating

KEY_BITS = 24
KEY_BYTES = KEY_BITS // 8

_HEX_DIGITS = frozenset("0123456789abcdefABCDEF")


class Tier1ClassicalError(ValueError):
    """Base class for errors raised by this module."""


class Tier1KeyError(Tier1ClassicalError):
    """The recovered key is not an integer in ``[0, 2**24)``."""


class Tier1CiphertextError(Tier1ClassicalError):
    """The ciphertext is not a non-empty, even-length hexadecimal string."""


class Tier1DecodeError(Tier1ClassicalError):
    """The decrypted bytes are not valid UTF-8."""


def key_to_bytes(key):
    """Return the 3-byte big-endian form of a 24-bit key.

    Leading zero bytes are preserved, so ``key_to_bytes(1)`` is
    ``b"\\x00\\x00\\x01"``.
    """
    if isinstance(key, bool) or not isinstance(key, int):
        raise Tier1KeyError(f"key must be an int, got {type(key).__name__}")
    if not 0 <= key < 1 << KEY_BITS:
        raise Tier1KeyError(f"key must satisfy 0 <= key < 2**{KEY_BITS}, got {key}")
    return key.to_bytes(KEY_BYTES, "big")


def ciphertext_to_bytes(ciphertext_hex):
    """Decode a hex ciphertext string into bytes.

    Whitespace inside the string is ignored.  Raises ``Tier1CiphertextError``
    for non-string input, empty input, odd length, or non-hexadecimal digits.
    """
    if not isinstance(ciphertext_hex, str):
        raise Tier1CiphertextError(
            f"ciphertext must be a hex string, got {type(ciphertext_hex).__name__}"
        )
    cleaned = "".join(ciphertext_hex.split())
    if not cleaned:
        raise Tier1CiphertextError("ciphertext must not be empty")
    if len(cleaned) % 2:
        raise Tier1CiphertextError("ciphertext hex must have an even number of digits")
    if set(cleaned) - _HEX_DIGITS:
        raise Tier1CiphertextError("ciphertext contains non-hexadecimal characters")
    return bytes.fromhex(cleaned)


def decrypt_tier1(key, ciphertext_hex):
    """Decrypt a Tier 1 ciphertext with the recovered 24-bit integer key.

    Returns the plaintext as a ``str``.  Raises ``Tier1KeyError``,
    ``Tier1CiphertextError`` or ``Tier1DecodeError`` for invalid input.
    """
    key_bytes = key_to_bytes(key)
    data = ciphertext_to_bytes(ciphertext_hex)
    plaintext = xor_repeating(data, key_bytes)
    try:
        return plaintext.decode("utf-8")
    except UnicodeDecodeError as error:
        raise Tier1DecodeError(
            f"decrypted bytes are not valid UTF-8 "
            f"({error.reason} at byte {error.start})"
        ) from error
