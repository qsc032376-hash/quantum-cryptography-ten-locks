"""Tier 7 classical side: 14-bit phase key conversion and keystream decryption.

Tier 7 hides an angle ``phi = k / 2**14`` and locks its line with
``keystream(format(k, "014b"), n)`` (``tier07/README.md``).  The quantum side
returns ``k``; this module turns a measured register into ``k`` and reuses the
shared keystream decryption from :mod:`classical_keystream`.

Register order is *not* assumed.  Qiskit prints counts most-significant
character first, and different QPE readouts place the phase bits differently,
so pick the converter that matches the circuit actually used:

* ``key_from_int(k)`` -- already an integer ``0 <= k < 2**14``.
* ``key_from_bitstring("c13...c0")`` -- the printed counts string, bit ``j`` of
  the string meaning classical bit ``c_j`` (i.e. qubit ``j``), value ``2**j``.
* ``key_from_qubit_bits([q0, q1, ...])`` -- one measured bit per qubit, in
  qubit order, with qubit ``j`` worth ``2**j``.
* ``key_from_reversed_register("c13...c0")`` -- for a readout where qubit 0
  carries the most significant phase bit (typical after an inverse QFT).  This
  reverses the string first; confirm the mapping against the actual circuit.
"""

import sys
from pathlib import Path

# Sibling module lives next to this file; keep the import independent of the cwd
# and of the team folder's name.
_TEAM_DIR = Path(__file__).resolve().parent
if str(_TEAM_DIR) not in sys.path:
    sys.path.insert(0, str(_TEAM_DIR))

from classical_keystream import (  # noqa: E402
    CiphertextError,
    DecodeError,
    KeyBitsError,
    decrypt_key_bits,
    key_bits_from_int,
    validate_key_bits,
)

WIDTH = 14

__all__ = [
    "CiphertextError",
    "DecodeError",
    "KeyBitsError",
    "WIDTH",
    "decrypt",
    "decrypt_bitstring",
    "key_bits_for",
    "key_from_bitstring",
    "key_from_int",
    "key_from_qubit_bits",
    "key_from_reversed_register",
]


def key_from_int(k):
    """Validate the canonical integer key and return it unchanged."""
    if isinstance(k, bool) or not isinstance(k, int):
        raise KeyBitsError(f"key must be an int, got {type(k).__name__}")
    if not 0 <= k < 1 << WIDTH:
        raise KeyBitsError(f"key must satisfy 0 <= k < 2**{WIDTH}, got {k}")
    return k


def _checked_bitstring(text):
    if not isinstance(text, str):
        raise KeyBitsError(f"bitstring must be a str, got {type(text).__name__}")
    if len(text) != WIDTH:
        raise KeyBitsError(f"bitstring must be {WIDTH} bits, got {len(text)}")
    if set(text) - {"0", "1"}:
        raise KeyBitsError("bitstring may only contain '0' and '1'")
    return text


def key_from_bitstring(text):
    """Read Qiskit counts order: ``c13 ... c0``, bit ``j`` worth ``2**j``."""
    return int(_checked_bitstring(text), 2)


def key_from_qubit_bits(bits):
    """Read one measured bit per qubit: ``bits[j]`` is qubit ``j``, worth ``2**j``."""
    bits = list(bits)
    if len(bits) != WIDTH:
        raise KeyBitsError(f"expected {WIDTH} bits, got {len(bits)}")
    value = 0
    for j, bit in enumerate(bits):
        if isinstance(bit, bool):
            bit = int(bit)
        if not isinstance(bit, int) or bit not in (0, 1):
            raise KeyBitsError(f"bit {j} must be 0 or 1, got {bit!r}")
        value |= bit << j
    return value


def key_from_reversed_register(text):
    """Read a register whose printed string has qubit 0 as the leading bit."""
    return key_from_bitstring(_checked_bitstring(text)[::-1])


def key_bits_for(k):
    """Return the official ``format(k, "014b")`` key string (leading zeros kept)."""
    return key_bits_from_int(key_from_int(k), WIDTH)


def decrypt(k, ciphertext_hex):
    """Decrypt tier 7 data with a 14-bit phase key integer."""
    return decrypt_key_bits(key_bits_for(k), WIDTH, ciphertext_hex)


def decrypt_bitstring(text, ciphertext_hex):
    """Decrypt from a Qiskit counts string (``c13 ... c0`` order)."""
    return decrypt(key_from_bitstring(text), ciphertext_hex)
