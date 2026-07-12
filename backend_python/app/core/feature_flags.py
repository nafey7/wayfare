"""Feature flags backed by AWS SSM Parameter Store.

Reads flags from ``/voya/{environment}/feature-flags/`` at startup.
Falls back to the Pydantic Settings default when SSM is unavailable
(local dev, missing permissions, etc.).

Toggle at runtime::

    aws ssm put-parameter \\
        --name /voya/production/feature-flags/public-chat \\
        --value false --overwrite --profile voya-admin

    # Restart ECS to pick up the change:
    aws ecs update-service --cluster production-cluster \\
        --service production-fastapi-react-service --force-new-deployment
"""

import logging

logger = logging.getLogger(__name__)

_FLAG_PREFIX: str | None = None
_flags: dict[str, bool] = {}
_loaded = False


def _ssm_prefix() -> str:
    """Build the SSM path prefix from the app environment."""
    global _FLAG_PREFIX
    if _FLAG_PREFIX is None:
        from app.core.config import settings

        _FLAG_PREFIX = f"/voya/{settings.ENVIRONMENT}/feature-flags"
    return _FLAG_PREFIX


def _load_flags() -> None:
    """Fetch all feature flags from SSM Parameter Store once at startup."""
    global _loaded
    if _loaded:
        return
    _loaded = True

    try:
        import boto3

        ssm = boto3.client("ssm")
        prefix = _ssm_prefix()
        paginator = ssm.get_paginator("get_parameters_by_path")
        for page in paginator.paginate(Path=prefix, Recursive=False):
            for param in page.get("Parameters", []):
                # /voya/production/feature-flags/public-chat -> public-chat
                flag_name = param["Name"].rsplit("/", 1)[-1]
                raw_value = param["Value"].lower().strip()
                _flags[flag_name] = raw_value in ("true", "1", "yes")
                logger.info(
                    "Feature flag %s = %s (from SSM)", flag_name, _flags[flag_name]
                )
    except Exception as exc:
        logger.warning("SSM feature flags unavailable, using defaults: %s", exc)


def get_flag(name: str, *, default: bool = False) -> bool:
    """Return a feature flag value. Loads from SSM on first call."""
    _load_flags()
    return _flags.get(name, default)


# Convenience accessors for known flags


def public_chat_enabled() -> bool:
    """Whether unauthenticated guest chat is enabled."""
    from app.core.config import settings

    return get_flag("public-chat", default=settings.VOYA_FEATURE_FLAG_PUBLIC_CHAT)
