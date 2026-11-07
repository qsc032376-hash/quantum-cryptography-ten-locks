"""Classical key handling and decryption for tiers 5 and 6 (toy byte cipher).

Both tiers share ``common.toy_cipher.ToyCipher`` and differ only in key width:

* Tier 5: 10-bit key, the plaintext starts with ``QC-05: `` and the first two
  bytes ``QC`` already pin down one key, so they are the classical filter.
* Tier 6: 14-bit key, about 64 keys decrypt the first byte ``Q`` correctly, so
  candidates are filtered by ``sum(plaintext) % 256`` against the public
  checksum (``tier06/helper.checksum``).

Key bit ``j`` has value ``2**j`` (``tier05/README.md``), i.e. the integer key
written little-endian.  A measured register ``c[n-1] ... c[0]`` therefore maps
to ``key_from_bits([c0, c1, ...])`` or ``key_from_bitstring("c...")``.

Only ``common`` is imported; no official file is modified or duplicated.
"""

import sys
from pathlib import Path

# Work from the repo root even when imported from a notebook or another cwd.
# Derived from this file, so it survives renaming the team folder.
_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from common.toy_cipher import ToyCipher

WIDTHS = {5: 10, 6: 14}

_HEX_DIGITS = frozenset("0123456789abcdefABCDEF")


class ToyCipherError(ValueError):
    """Base class for errors raised by this module."""


class KeyFormatError(ToyCipherError):
    """The candidate key cannot be written as an integer of the tier's width."""


class CiphertextError(ToyCipherError):
    """The ciphertext is not a non-empty, even-length hexadecimal string."""


class DecodeError(ToyCipherError):
    """The decrypted bytes are not valid UTF-8."""


class ChecksumError(ToyCipherError):
    """A tier 6 candidate failed the public checksum filter."""

    def __init__(self, key, expected, actual):
        super().__init__(
            f"key {key}: checksum {actual} does not match the public {expected}"
        )
        self.key = key
        self.expected = expected
        self.actual = actual


def width_for(tier):
    """Return the key width in bits for tier 5 or tier 6."""
    try:
        return WIDTHS[tier]
    except (KeyError, TypeError):
        raise ToyCipherError(f"tier must be 5 or 6, got {tier!r}") from None


def _check_width(key_bits):
    if key_bits not in WIDTHS.values():
        raise ToyCipherError(f"unsupported key width {key_bits}")


def key_from_int(value, key_bits):
    """Validate an integer key written with bit ``j`` = ``2**j``."""
    _check_width(key_bits)
    if isinstance(value, bool) or not isinstance(value, int):
        raise KeyFormatError(f"key must be an int, got {type(value).__name__}")
    if not 0 <= value < 1 << key_bits:
        raise KeyFormatError(
            f"key must satisfy 0 <= key < 2**{key_bits}, got {value}"
        )
    return value


def key_from_bits(bits, key_bits):
    """Build the integer key from measured bits in qubit order.

    ``bits[j]`` is the value on key qubit ``j`` and therefore has weight
    ``2**j``.  Leading zeros are simply absent qubits, so they need no padding.
    """
    _check_width(key_bits)
    bits = list(bits)
    if len(bits) != key_bits:
        raise KeyFormatError(f"expected {key_bits} bits, got {len(bits)}")
    value = 0
    for j, bit in enumerate(bits):
        if isinstance(bit, bool):
            bit = int(bit)
        if not isinstance(bit, int) or bit not in (0, 1):
            raise KeyFormatError(f"bit {j} must be 0 or 1, got {bit!r}")
        value |= bit << j
    return value


def key_from_bitstring(text, key_bits):
    """Build the integer key from a most-significant-bit-first string.

    Qiskit prints a register as ``c[n-1] ... c[0]``, which is exactly this
    order, so ``key_from_bitstring("0000000001", 10)`` is the key ``1``.
    """
    _check_width(key_bits)
    if not isinstance(text, str):
        raise KeyFormatError(f"bitstring must be a str, got {type(text).__name__}")
    if len(text) != key_bits:
        raise KeyFormatError(f"expected {key_bits} bits, got {len(text)}")
    if set(text) - {"0", "1"}:
        raise KeyFormatError("bitstring may only contain '0' and '1'")
    return int(text, 2)


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


def checksum(data):
    """Official tier 6 checksum: sum of the plaintext bytes modulo 256."""
    return sum(data) % 256


def decrypt_bytes(tier, key, ciphertext_hex):
    """Decrypt to bytes with the official ``ToyCipher``; no text decoding."""
    key_bits = width_for(tier)
    key = key_from_int(key, key_bits)
    data = ciphertext_to_bytes(ciphertext_hex)
    return ToyCipher(key, key_bits).decrypt(data)


def decrypt(tier, key, ciphertext_hex):
    """Decrypt tier 5 or tier 6 data and return the plaintext as ``str``."""
    plaintext = decrypt_bytes(tier, key, ciphertext_hex)
    try:
        return plaintext.decode("utf-8")
    except UnicodeDecodeError as error:
        raise DecodeError(
            f"decrypted bytes are not valid UTF-8 "
            f"({error.reason} at byte {error.start})"
        ) from error


def decrypt_tier5(key, ciphertext_hex):
    """Tier 5: 10-bit key, plaintext starts with ``QC-05: ``."""
    return decrypt(5, key, ciphertext_hex)


def decrypt_tier6(key, ciphertext_hex, expected_checksum):
    """Tier 6: decrypt, then enforce the public checksum filter.

    Raises ``ChecksumError`` for a candidate that decrypts to the wrong byte
    sum, which is the normal outcome for the ~64 keys matching the first byte.
    """
    if isinstance(expected_checksum, bool) or not isinstance(expected_checksum, int):
        raise ToyCipherError("expected_checksum must be an int")
    if not 0 <= expected_checksum <= 255:
        raise ToyCipherError("expected_checksum must be between 0 and 255")
    key = key_from_int(key, WIDTHS[6])
    plaintext = decrypt_bytes(6, key, ciphertext_hex)
    actual = checksum(plaintext)
    if actual != expected_checksum:
        raise ChecksumError(key, expected_checksum, actual)
    try:
        return plaintext.decode("utf-8")
    except UnicodeDecodeError as error:
        raise DecodeError(
            f"decrypted bytes are not valid UTF-8 "
            f"({error.reason} at byte {error.start})"
        ) from error


def matches_prefix(key, ciphertext_hex, prefix=b"QC", tier=5):
    """Classical pre-filter: does this key decrypt to the known prefix?"""
    return decrypt_bytes(tier, key, ciphertext_hex).startswith(prefix)


def filter_candidates(tier, candidates, ciphertext_hex, expected_checksum=None):
    """Return the plaintexts of candidates that pass the tier's classical filter.

    Tier 5 keeps every candidate whose plaintext is valid UTF-8 (the first two
    bytes ``QC`` are checked by the quantum oracle); tier 6 additionally
    requires the public checksum.  Bad candidates are skipped, not raised.
    """
    accepted = []
    for candidate in candidates:
        try:
            if tier == 6:
                accepted.append(decrypt_tier6(candidate, ciphertext_hex, expected_checksum))
            else:
                accepted.append(decrypt(tier, candidate, ciphertext_hex))
        except (ToyCipherError, UnicodeDecodeError):
            continue
    return accepted
