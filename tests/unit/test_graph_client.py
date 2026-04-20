import pytest
import respx
import httpx

from sharepoint_checker.graph_client import GraphClient
from sharepoint_checker.utils.retry import GraphApiError, ThrottledError


class FakeTokenProvider:
    def get_token(self) -> str:
        return "fake-token"


GRAPH_BASE = "https://graph.microsoft.com/v1.0"


@pytest.fixture
def client():
    return GraphClient(FakeTokenProvider(), page_size=10, retry_attempts=2, retry_backoff_seconds=0.01)


@pytest.mark.asyncio
async def test_get_success(client):
    with respx.mock:
        respx.get(f"{GRAPH_BASE}/sites").mock(
            return_value=httpx.Response(200, json={"value": [{"id": "site1"}]})
        )
        async with client:
            data = await client.get(client.url("/sites"))
    assert data["value"][0]["id"] == "site1"


@pytest.mark.asyncio
async def test_get_raises_on_4xx(client):
    with respx.mock:
        respx.get(f"{GRAPH_BASE}/sites").mock(
            return_value=httpx.Response(403, json={"error": {"message": "Forbidden"}})
        )
        async with client:
            with pytest.raises(GraphApiError) as exc_info:
                await client.get(client.url("/sites"))
    assert exc_info.value.status_code == 403


@pytest.mark.asyncio
async def test_get_raises_throttled_on_429(client):
    with respx.mock:
        respx.get(f"{GRAPH_BASE}/sites").mock(
            return_value=httpx.Response(429, headers={"Retry-After": "5"})
        )
        async with client:
            with pytest.raises(ThrottledError) as exc_info:
                await client._raw_get(client.url("/sites"))
    assert exc_info.value.retry_after == 5.0


@pytest.mark.asyncio
async def test_get_paginated_follows_next_link(client):
    responses = [
        httpx.Response(200, json={"value": [{"id": "a"}, {"id": "b"}], "@odata.nextLink": f"{GRAPH_BASE}/sites?$skiptoken=abc"}),
        httpx.Response(200, json={"value": [{"id": "c"}]}),
    ]

    with respx.mock:
        respx.get(url__regex=r".*/sites.*").mock(side_effect=responses)
        async with client:
            items = await client.get_paginated(client.url("/sites"))

    assert [i["id"] for i in items] == ["a", "b", "c"]
