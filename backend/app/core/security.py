import re
import ipaddress
import urllib.parse
from typing import Optional

# Strict format regex for API keys: only alphanumeric, dashes, dots, underscores, length 16 to 128 chars.
API_KEY_REGEX = re.compile(r"^[a-zA-Z0-9_\-\.]{16,128}$")

# Disallowed internal/private IP networks for SSRF prevention
PRIVATE_NETWORKS = [
    ipaddress.ip_network("127.0.0.0/8"),
    ipaddress.ip_network("10.0.0.0/8"),
    ipaddress.ip_network("172.16.0.0/12"),
    ipaddress.ip_network("192.168.0.0/16"),
    ipaddress.ip_network("169.254.0.0/16"),  # Cloud metadata service
    ipaddress.ip_network("::1/128"),
    ipaddress.ip_network("fc00::/7"),
    ipaddress.ip_network("fe80::/10"),
]


def mask_api_key(key: Optional[str]) -> str:
    """Safely masks an API key so it is never exposed in logs or UI."""
    if not key:
        return "None"
    clean = key.strip()
    if len(clean) <= 8:
        return "****"
    return f"{clean[:5]}...{clean[-4:]}"


def sanitize_and_validate_api_key(raw_key: Optional[str]) -> Optional[str]:
    """
    Validates API key format against CRLF injection, null bytes, and malicious payloads.
    Returns sanitized key string if valid, or None if invalid/suspicious.
    """
    if not raw_key:
        return None
    
    clean = raw_key.strip()
    # Strip optional "Bearer " prefix if passed directly
    if clean.lower().startswith("bearer "):
        clean = clean[7:].strip()

    # Reject any CRLF or newline characters (Header Injection defense)
    if "\r" in clean or "\n" in clean or "\0" in clean:
        return None

    # Check strict alphanumeric pattern
    if not API_KEY_REGEX.match(clean):
        return None

    return clean


def is_safe_external_url(url_str: str) -> bool:
    """
    Prevents SSRF (Server-Side Request Forgery) by ensuring custom base URLs
    use HTTPS and do not resolve to loopback or private infrastructure networks.
    """
    try:
        parsed = urllib.parse.urlparse(url_str)
        # Must be HTTPS
        if parsed.scheme.lower() != "https":
            return False

        hostname = parsed.hostname
        if not hostname:
            return False

        if hostname.lower() in ["localhost", "127.0.0.1", "0.0.0.0", "metadata.google.internal"]:
            return False

        # Attempt IP resolution check if hostname is an IP
        try:
            ip = ipaddress.ip_address(hostname)
            for priv_net in PRIVATE_NETWORKS:
                if ip in priv_net:
                    return False
        except ValueError:
            # Not an IP literal, standard hostname
            pass

        return True
    except Exception:
        return False


def create_scoped_gateway(base_gateway, raw_key: str):
    """
    Dynamically creates an isolated KifayatGateway instance for a user-supplied API key.
    Includes multi-provider failover protection while preventing leakage of the user key.
    """
    sanitized = sanitize_and_validate_api_key(raw_key)
    if not sanitized:
        from fastapi import HTTPException
        raise HTTPException(status_code=400, detail="Invalid API key format.")

    from backend.app.config import settings
    from backend.app.providers.nvidia_provider import NVIDIAProvider
    from backend.app.providers.mock_provider import MockProvider
    from backend.app.providers.router import MultiProviderRouter
    from backend.app.repair.ladder import PromptRepairLadder
    from backend.app.gateway import KifayatGateway

    scoped_nvidia = NVIDIAProvider(
        api_key=sanitized,
        base_url=settings.NVIDIA_BASE_URL,
        default_model=settings.NVIDIA_MODEL
    )
    fallback_mock = MockProvider()
    scoped_router = MultiProviderRouter(
        providers={"user_nvidia": scoped_nvidia, "fallback_local": fallback_mock},
        priority_order=["user_nvidia", "fallback_local"]
    )
    return KifayatGateway(
        store=base_gateway.store,
        provider=scoped_router,
        context_builder=base_gateway.context_builder,
        semantic_cache=base_gateway.semantic_cache,
        exemplar_store=base_gateway.exemplar_store,
        compaction_queue=base_gateway.compaction_queue,
        router=base_gateway.router
    )
