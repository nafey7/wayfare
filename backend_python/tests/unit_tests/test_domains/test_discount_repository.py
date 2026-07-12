"""Unit tests for discount MongoDB repository (filters, aggregations)."""

import re
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.domains.discount.repository import DiscountRepository, discount_repository


class _EmptyAsyncCursor:
    def sort(self, *_a, **_k):
        return self

    def skip(self, *_a, **_k):
        return self

    def limit(self, *_a, **_k):
        return self

    def __aiter__(self):
        return self

    async def __anext__(self):
        raise StopAsyncIteration


@pytest.mark.asyncio
async def test_list_discounts_escapes_search_for_regex() -> None:
    """Admin search is substring match; ReDoS patterns must be escaped."""
    mock_coll = MagicMock()
    mock_coll.count_documents = AsyncMock(return_value=0)
    mock_coll.find = MagicMock(return_value=_EmptyAsyncCursor())
    repo = DiscountRepository(collection=mock_coll)
    pat = "VOYA(a+)+$"
    await repo.list_discounts(
        status=None,
        batch_id=None,
        source=None,
        search=pat,
        limit=10,
        offset=0,
    )
    filt = mock_coll.find.call_args[0][0]
    assert filt["code"]["$regex"] == re.escape(pat)
    assert filt["code"]["$options"] == "i"


@pytest.mark.asyncio
async def test_aggregate_batch_summaries_with_batch_id_matches() -> None:
    mock_coll = MagicMock()
    mock_agg = MagicMock()
    mock_agg.to_list = AsyncMock(
        return_value=[{"_id": "b-target", "total": 1, "source": "g2a"}]
    )
    mock_coll.aggregate = MagicMock(return_value=mock_agg)
    repo = DiscountRepository(collection=mock_coll)
    out = await repo.aggregate_batch_summaries(batch_id="b-target")
    assert out
    assert str(out[0]["_id"]) == "b-target"
    pipeline = mock_coll.aggregate.call_args[0][0]
    assert pipeline[0] == {"$match": {"batch_id": "b-target"}}


def test_module_singleton_uses_class() -> None:
    assert isinstance(discount_repository, DiscountRepository)
