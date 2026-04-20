import pytest
from unittest.mock import AsyncMock, MagicMock

from sharepoint_checker.site_discovery import SiteDiscovery
from sharepoint_checker.models.config_models import DiscoveryConfig

SITE_A = {"id": "s1", "name": "EPAMSAPProjects", "webUrl": "https://epam.sharepoint.com/sites/EPAMSAPProjects", "displayName": "EPAM SAP"}
SITE_B = {"id": "s2", "name": "OtherTeam", "webUrl": "https://epam.sharepoint.com/sites/OtherTeam", "displayName": "Other"}
SITE_C = {"id": "s3", "name": "EPAMSAPSEProjects", "webUrl": "https://epam.sharepoint.com/sites/EPAMSAPSEProjects", "displayName": "EPAM SAP SE"}


@pytest.fixture
def mock_client():
    client = MagicMock()
    client.url = lambda path: f"https://graph.microsoft.com/v1.0{path}"
    client.get_paginated = AsyncMock()
    return client


@pytest.mark.asyncio
async def test_prefix_mode_discovers_by_keyword(mock_client):
    mock_client.get_paginated.return_value = [SITE_A, SITE_C]
    config = DiscoveryConfig(mode="prefix", search_keywords=["EPAMSAPProjects"])
    discovery = SiteDiscovery(mock_client, config)
    sites = await discovery.discover()
    assert len(sites) == 2
    assert sites[0].site_id == "s1"


@pytest.mark.asyncio
async def test_include_url_pattern_filter(mock_client):
    mock_client.get_paginated.return_value = [SITE_A, SITE_B, SITE_C]
    config = DiscoveryConfig(
        mode="prefix",
        search_keywords=["EPAM"],
        include_site_url_patterns=["/sites/EPAMSAPSEProjects"],
    )
    discovery = SiteDiscovery(mock_client, config)
    sites = await discovery.discover()
    assert len(sites) == 1
    assert sites[0].site_url == SITE_C["webUrl"]


@pytest.mark.asyncio
async def test_exclude_url_pattern_filter(mock_client):
    mock_client.get_paginated.return_value = [SITE_A, SITE_B, SITE_C]
    config = DiscoveryConfig(
        mode="prefix",
        search_keywords=["EPAM"],
        exclude_site_url_patterns=["/sites/OtherTeam"],
    )
    discovery = SiteDiscovery(mock_client, config)
    sites = await discovery.discover()
    assert all(s.site_name != "OtherTeam" for s in sites)


@pytest.mark.asyncio
async def test_all_visible_mode(mock_client):
    mock_client.get_paginated.return_value = [SITE_A, SITE_B]
    config = DiscoveryConfig(mode="all-visible")
    discovery = SiteDiscovery(mock_client, config)
    sites = await discovery.discover()
    assert len(sites) == 2


@pytest.mark.asyncio
async def test_deduplication_across_keywords(mock_client):
    mock_client.get_paginated.side_effect = [[SITE_A, SITE_C], [SITE_C]]
    config = DiscoveryConfig(
        mode="prefix",
        search_keywords=["EPAMSAPProjects", "EPAMSAPSEProjects"],
    )
    discovery = SiteDiscovery(mock_client, config)
    sites = await discovery.discover()
    ids = [s.site_id for s in sites]
    assert ids.count("s3") == 1
