"""Classical SHA-256 keystream decryption shared by tiers 3 and 4.

Both tiers mask their plaintext with ``common.crypto.keystream(key_bits, n)``
and XOR, and they differ only in how the key is written:

* Tier 3: 24 bits in oracle order, oracle 0 first, 0 = constant and 1 = balanced
  (``tier03/README.md``).
* Tier 4: 10 bits, ``key_bits = format(s, "010b")``, i.e. most significant bit of
  ``s`` first and zero padded (``tier04/README.md``).

This module turns a recovered key into that string, validates it, and applies
the official ``keystream``/``xor_bytes`` helpers.  It builds no circuits.
"""

from common.crypto import keystream, xor_bytes

WIDTHS = {3: 24, 4: 10}

_HEX_DIGITS = frozenset("0123456789abcdefABCDEF")


class KeystreamError(ValueError):
    """Base class for errors raised by this module."""


class KeyBitsError(KeystreamError):
    """The recovered key cannot be written as the required bit string."""


class CiphertextError(KeystreamError):
    """The ciphertext is not a non-empty, even-length hexadecimal string."""


class DecodeError(KeystreamError):
    """The decrypted bytes are not valid UTF-8."""


def width_for(tier):
    """Return the key width in bits for tier 3 or tier 4."""
    try:
        return WIDTHS[tier]
    except (KeyError, TypeError):
        raise KeystreamError(f"tier must be 3 or 4, got {tier!r}") from None


def key_bits_from_int(value, width):
    """Return ``width`` bits of ``value``, most significant bit first.

    Leading zeros are preserved: ``key_bits_from_int(1, 10)`` is
    ``"0000000001"``.
    """
    if isinstance(value, bool) or not isinstance(value, int):
        raise KeyBitsError(f"key must be an int, got {type(value).__name__}")
    if width <= 0:
        raise KeyBitsError(f"width must be positive, got {width}")
    if not 0 <= value < 1 << width:
        raise KeyBitsError(f"key must satisfy 0 <= key < 2**{width}, got {value}")
    return format(value, f"0{width}b")


def key_bits_from_flags(flags, width=24):
    """Join per-oracle flags (0 = constant, 1 = balanced) in oracle order.

    Used by tier 3, where flag ``i`` is the result for oracle ``i``.
    """
    flags = list(flags)
    if len(flags) != width:
        raise KeyBitsError(f"expected {width} flags, got {len(flags)}")
    bits = []
    for index, flag in enumerate(flags):
        if isinstance(flag, bool):
            flag = int(flag)
        if not isinstance(flag, int) or flag not in (0, 1):
            raise KeyBitsError(f"flag {index} must be 0 or 1, got {flag!r}")
        bits.append(str(flag))
    return "".join(bits)


def validate_key_bits(key_bits, width):
    """Check an already-written key string and return it unchanged."""
    if not isinstance(key_bits, str):
        raise KeyBitsError(
            f"key_bits must be a string, got {type(key_bits).__name__}"
        )
    if len(key_bits) != width:
        raise KeyBitsError(f"key_bits must be {width} bits, got {len(key_bits)}")
    if set(key_bits) - {"0", "1"}:
        raise KeyBitsError("key_bits may only contain '0' and '1'")
    return key_bits


def ciphertext_to_bytes(ciphertext_hex):
    """Decode a hex ciphertext, ignoring internal whitespace."""
    if not isinstance(ciphertext_hex, str):
        raise CiphertextError(
            f"ciphertext must be a hex string, got {type(ciphertext_hex).__name__}"
        )
    cleaned = "".join(ciphertext_hex.split())
    if not cleaned:
        raise CiphertextError("ciphertext must not be empty")
    if len(cleaned) % 2:
        raise CiphertextError("ciphertext hex must have an even number of digits")
    if set(cleaned) - _HEX_DIGITS:
        raise CiphertextError("ciphertext contains non-hexadecimal characters")
    return bytes.fromhex(cleaned)


def decrypt_key_bits(key_bits, width, ciphertext_hex):
    """Decrypt with a ready-made ``width``-bit key string."""
    key_bits = validate_key_bits(key_bits, width)
    data = ciphertext_to_bytes(ciphertext_hex)
    try:
        plaintext = xor_bytes(data, keystream(key_bits, len(data)))
    except ValueError as error:
        raise KeystreamError(str(error)) from error
    try:
        return plaintext.decode("utf-8")
    except UnicodeDecodeError as error:
        raise DecodeError(
            f"decrypted bytes are not valid UTF-8 "
            f"({error.reason} at byte {error.start})"
        ) from error


def decrypt(tier, key_bits, ciphertext_hex):
    """Decrypt tier 3 or tier 4 data from a key string of the right width."""
    return decrypt_key_bits(key_bits, width_for(tier), ciphertext_hex)


def decrypt_tier3(flags, ciphertext_hex):
    """Tier 3: 24 per-oracle flags (0/1) in oracle order, oracle 0 first."""
    return decrypt_key_bits(
        key_bits_from_flags(flags, WIDTHS[3]), WIDTHS[3], ciphertext_hex
    )


def decrypt_tier4(s, ciphertext_hex):
    """Tier 4: the recovered 10-bit integer ``s``, written as ``format(s, "010b")``."""
    return decrypt_key_bits(
        key_bits_from_int(s, WIDTHS[4]), WIDTHS[4], ciphertext_hex
    )


def encrypt_key_bits(key_bits, width, plaintext):
    """Symmetric helper used only by round-trip tests: returns ciphertext hex."""
    key_bits = validate_key_bits(key_bits, width)
    data = plaintext.encode("utf-8")
    return xor_bytes(data, keystream(key_bits, len(data))).hex()
