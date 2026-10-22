from __future__ import annotations

from datetime import UTC

from agentos.utils import new_id, utc_now


def test_new_id_returns_unique_values() -> None:
    """new_id should return non-empty unique values."""
    assert new_id() != new_id()


def test_utc_now_is_timezone_aware() -> None:
    """utc_now should return timezone-aware UTC datetimes."""
    assert utc_now().tzinfo == UTC
