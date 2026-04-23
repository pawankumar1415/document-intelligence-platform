"""
sharepoint_service.py — Microsoft Graph API integration for SharePoint file access.

Authentication uses the OAuth2 Client Credentials flow (app-only, no user sign-in
required).  The app needs the following Microsoft Graph application permissions
granted and admin-consented in your Azure App Registration:
    - Sites.Read.All
    - Files.Read.All

Required environment variables (.env):
    SHAREPOINT_TENANT_ID      — Azure AD Tenant ID (Directory ID)
    SHAREPOINT_CLIENT_ID      — App Registration Application (client) ID
    SHAREPOINT_CLIENT_SECRET  — Client secret value
    SHAREPOINT_SITE_URL       — Full URL of the target SharePoint site
                                e.g. https://yourtenant.sharepoint.com/sites/yoursite

How to find these values:
    1. SHAREPOINT_TENANT_ID:
       Azure Portal → Azure Active Directory → Overview → Tenant ID

    2. SHAREPOINT_CLIENT_ID:
       Azure Portal → Azure AD → App Registrations → your app → Application (client) ID

    3. SHAREPOINT_CLIENT_SECRET:
       Azure Portal → Azure AD → App Registrations → your app
       → Certificates & Secrets → New client secret → copy the Value

    4. SHAREPOINT_SITE_URL:
       Open the SharePoint site in your browser, copy the URL up to and including
       the site name: https://yourtenant.sharepoint.com/sites/yoursite

    5. Grant permissions:
       App Registration → API Permissions → Add a permission
       → Microsoft Graph → Application permissions
       → Add Sites.Read.All and Files.Read.All → Grant admin consent
"""

from __future__ import annotations

import logging
from typing import Any

from backend.app.config import env

logger = logging.getLogger(__name__)

# ── Configuration placeholders ────────────────────────────────────────────────
# Replace these with real values in your .env file.

TENANT_ID = env("SHAREPOINT_TENANT_ID", "YOUR_TENANT_ID_HERE")
CLIENT_ID = env("SHAREPOINT_CLIENT_ID", "YOUR_CLIENT_ID_HERE")
CLIENT_SECRET = env("SHAREPOINT_CLIENT_SECRET", "YOUR_CLIENT_SECRET_HERE")
SITE_URL = env("SHAREPOINT_SITE_URL", "https://yourtenant.sharepoint.com/sites/yoursite")

_GRAPH_BASE = "https://graph.microsoft.com/v1.0"


def _is_configured() -> bool:
    """Return True only if all four credentials are set to real (non-placeholder) values."""
    return all([
        TENANT_ID and TENANT_ID != "YOUR_TENANT_ID_HERE",
        CLIENT_ID and CLIENT_ID != "YOUR_CLIENT_ID_HERE",
        CLIENT_SECRET and CLIENT_SECRET != "YOUR_CLIENT_SECRET_HERE",
        SITE_URL and "yourtenant" not in (SITE_URL or ""),
    ])


def _get_access_token() -> str:
    """Obtain a bearer token via the OAuth2 client credentials flow."""
    try:
        import msal
    except ModuleNotFoundError as exc:
        raise RuntimeError(
            "msal is not installed. Run: pip install msal"
        ) from exc

    authority = f"https://login.microsoftonline.com/{TENANT_ID}"
    app = msal.ConfidentialClientApplication(
        client_id=CLIENT_ID,
        client_credential=CLIENT_SECRET,
        authority=authority,
    )
    result = app.acquire_token_for_client(scopes=["https://graph.microsoft.com/.default"])
    if "access_token" not in result:
        error = result.get("error_description", result.get("error", "Unknown auth error"))
        raise RuntimeError(f"SharePoint authentication failed: {error}")
    return str(result["access_token"])


def _graph_get(path: str, token: str) -> dict[str, Any]:
    """Make a GET request to Microsoft Graph and return parsed JSON."""
    import urllib.request
    import urllib.error
    import json

    url = f"{_GRAPH_BASE}{path}"
    req = urllib.request.Request(
        url,
        headers={"Authorization": f"Bearer {token}", "Accept": "application/json"},
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"Graph API error {exc.code} for {path}: {body}") from exc


def _graph_download(path: str, token: str) -> bytes:
    """Download binary content from Microsoft Graph."""
    import urllib.request
    import urllib.error

    url = f"{_GRAPH_BASE}{path}"
    req = urllib.request.Request(
        url,
        headers={"Authorization": f"Bearer {token}"},
    )
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            return resp.read()
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"Graph API download error {exc.code}: {body}") from exc


def _get_site_id(token: str) -> str:
    """
    Resolve SHAREPOINT_SITE_URL to a Graph site ID.

    Strategy (in order):
    1. Direct lookup via hostname:path — fastest, works when tenant matches.
    2. Search fallback via /sites?search=* — matches by webUrl when direct
       lookup returns 400 (common when TENANT_ID is a GUID but the hostname
       routes to a different tenant partition).
    3. Tenant-scoped URL using the hostname from SITE_URL with explicit path.
    """
    url = (SITE_URL or "").rstrip("/")
    if "://" in url:
        url = url.split("://", 1)[1]
    parts = url.split("/", 1)
    hostname = parts[0]
    site_path = "/" + parts[1] if len(parts) > 1 else "/"

    # Strategy 1: direct hostname:path lookup
    try:
        data = _graph_get(f"/sites/{hostname}:{site_path}", token)
        return str(data["id"])
    except RuntimeError as exc:
        if "400" not in str(exc) and "403" not in str(exc):
            raise
        logger.warning(
            "Direct site lookup failed (%s). Falling back to site search.", exc
        )

    # Strategy 2: search all accessible sites and match by URL
    target_url = (SITE_URL or "").rstrip("/").lower()
    try:
        data = _graph_get("/sites?search=*", token)
        for site in data.get("value", []):
            web_url = (site.get("webUrl") or "").rstrip("/").lower()
            if web_url == target_url or web_url in target_url or target_url in web_url:
                site_id = str(site["id"])
                logger.info("Resolved site via search: %s → %s", SITE_URL, site_id)
                return site_id
    except RuntimeError as search_exc:
        logger.warning("Site search fallback also failed: %s", search_exc)

    raise RuntimeError(
        f"Cannot resolve SharePoint site '{SITE_URL}'. "
        "Possible causes:\n"
        "  1. SHAREPOINT_TENANT_ID does not match the tenant that owns this SharePoint hostname.\n"
        "     Fix: go to https://login.microsoftonline.com/<your-hostname>.onmicrosoft.com/.well-known/openid-configuration "
        "and copy the 'token_endpoint' GUID — that is your real Tenant ID.\n"
        "  2. The app registration lacks Sites.Read.All permission (or admin consent was not granted).\n"
        "  3. SHAREPOINT_SITE_URL is misspelled or the site does not exist."
    )


# ── Public API ─────────────────────────────────────────────────────────────────

def list_sites() -> list[dict[str, str]]:
    """List SharePoint sites accessible to the app."""
    if not _is_configured():
        raise RuntimeError("SharePoint credentials are not configured. Set SHAREPOINT_TENANT_ID, SHAREPOINT_CLIENT_ID, SHAREPOINT_CLIENT_SECRET, and SHAREPOINT_SITE_URL in your .env file.")

    token = _get_access_token()
    data = _graph_get("/sites?search=*", token)
    sites = []
    for item in data.get("value", []):
        sites.append({
            "id": item["id"],
            "name": item.get("displayName") or item.get("name", ""),
            "web_url": item.get("webUrl", ""),
        })
    return sites


def list_libraries(site_id: str | None = None) -> list[dict[str, str]]:
    """List document libraries (drives) in the configured SharePoint site."""
    if not _is_configured():
        raise RuntimeError("SharePoint credentials are not configured.")

    token = _get_access_token()
    resolved_site_id = site_id or _get_site_id(token)
    data = _graph_get(f"/sites/{resolved_site_id}/drives", token)

    libraries = []
    for drive in data.get("value", []):
        libraries.append({
            "id": drive["id"],
            "name": drive.get("name", ""),
            "web_url": drive.get("webUrl", ""),
        })
    return libraries


def list_files(library_id: str, folder_path: str = "/") -> list[dict[str, Any]]:
    """
    List files and folders in a SharePoint document library at the given folder path.
    folder_path: "/" for root, "/FolderName" for a subfolder.
    """
    if not _is_configured():
        raise RuntimeError("SharePoint credentials are not configured.")

    token = _get_access_token()
    folder_path = folder_path.rstrip("/") or "/"

    if folder_path == "/":
        path = f"/drives/{library_id}/root/children"
    else:
        import urllib.parse
        encoded = urllib.parse.quote(folder_path.lstrip("/"), safe="/")
        path = f"/drives/{library_id}/root:/{encoded}:/children"

    data = _graph_get(path, token)
    items = []
    for item in data.get("value", []):
        is_folder = "folder" in item
        items.append({
            "id": item["id"],
            "name": item.get("name", ""),
            "size": item.get("size", 0),
            "last_modified": item.get("lastModifiedDateTime", ""),
            "web_url": item.get("webUrl", ""),
            "mime_type": item.get("file", {}).get("mimeType", "") if not is_folder else "",
            "is_folder": is_folder,
        })
    # Sort: folders first, then files alphabetically
    items.sort(key=lambda x: (not x["is_folder"], x["name"].lower()))
    return items


def download_file(library_id: str, item_id: str) -> bytes:
    """Download file content bytes from SharePoint by item ID."""
    if not _is_configured():
        raise RuntimeError("SharePoint credentials are not configured.")

    token = _get_access_token()
    return _graph_download(f"/drives/{library_id}/items/{item_id}/content", token)


def is_configured() -> bool:
    return _is_configured()