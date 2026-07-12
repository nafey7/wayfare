"""ActiveCampaign integration module."""

from .client import (
    ActiveCampaignClient,
    ContactSyncResult,
    get_activecampaign_client,
)

__all__ = [
    "ActiveCampaignClient",
    "ContactSyncResult",
    "get_activecampaign_client",
]
