"""Fast unit coverage for pure normalization, token, and cache helpers."""

import uuid
from datetime import date, datetime, time, timezone

from app.api.v1.todos import _as_utc_bounds, _todo_cache_key
from app.services.auth_service import normalize_email
from app.services.session_service import hash_refresh_token


def test_normalize_email_uses_one_canonical_identity() -> None:
    assert normalize_email("  User@Example.COM ") == "user@example.com"


def test_refresh_token_hash_is_deterministic_and_one_way_length() -> None:
    first = hash_refresh_token("refresh-token")
    second = hash_refresh_token("refresh-token")

    assert first == second
    assert len(first) == 64
    assert first != "refresh-token"


def test_todo_cache_key_contains_every_filter_dimension() -> None:
    user_id = uuid.uuid4()
    tag_id = uuid.uuid4()

    key = _todo_cache_key(
        user_id,
        page=2,
        page_size=50,
        status_filter="completed",
        tag_id=tag_id,
        keyword="  Release  ",
        date_from=date(2026, 10, 1),
        date_to=date(2026, 10, 6),
    )

    assert key.startswith(f"todos:user:{user_id}:")
    assert "page=2" in key
    assert "page_size=50" in key
    assert "status=completed" in key
    assert f"tag={tag_id}" in key
    assert "keyword=release" in key
    assert "from=2026-10-01" in key
    assert "to=2026-10-06" in key


def test_date_filter_bounds_are_utc_and_date_to_is_exclusive() -> None:
    start, end = _as_utc_bounds(date(2026, 10, 1), date(2026, 10, 6))

    assert start == datetime.combine(date(2026, 10, 1), time.min, timezone.utc)
    assert end == datetime.combine(date(2026, 10, 7), time.min, timezone.utc)
