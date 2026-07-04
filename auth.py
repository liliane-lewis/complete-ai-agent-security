import os
from dotenv import load_dotenv

load_dotenv()

AD_SERVER  = os.environ.get("AD_SERVER",  "192.168.10.100")
AD_DOMAIN  = os.environ.get("AD_DOMAIN",  "corp")
AD_BASE_DN = os.environ.get("AD_BASE_DN", "DC=corp,DC=local")
AUTH_MODE  = os.environ.get("AUTH_MODE",  "ad")   # "ad" or "local"

# ── Local fallback users ───────────────────────────────────────────────────────
# Same format as AD auth return — compatible with index.html and agent system prompt.
# VULNERABLE by design: description field contains exposed passwords.
LOCAL_USERS = {
    "ethompson": {
        "password":    "Corp@123",
        "username":    "ethompson",
        "name":        "Emily Thompson",
        "department":  "HR",
        "title":       "HR Manager",
        "description": "Temp password Corp@123",   # VULNERABLE: password in description
        "email":       "ethompson@corp.local",
        "groups":      ["CN=HR,DC=corp,DC=local"],
        "tier":        "Basic",
    },
    "mtorres": {
        "password":    "Corp@123",
        "username":    "mtorres",
        "name":        "Miguel Torres",
        "department":  "Finance",
        "title":       "Financial Analyst",
        "description": "Temp password Corp@123",   # VULNERABLE: password in description
        "email":       "mtorres@corp.local",
        "groups":      ["CN=Finance,DC=corp,DC=local"],
        "tier":        "Basic",
    },
    "janderson": {
        "password":    "Corp@456",
        "username":    "janderson",
        "name":        "James Anderson",
        "department":  "IT",
        "title":       "Systems Administrator",
        "description": "[]",
        "email":       "janderson@corp.local",
        "groups":      ["CN=IT,DC=corp,DC=local"],
        "tier":        "Gold",
    },
    "svc_aircorp": {
        "password":    "AirCorp2024!",
        "username":    "svc_aircorp",
        "name":        "AirCorp Service Account",
        "department":  "IT",
        "title":       "Service Account",
        "description": "AirCorp service account - AirC0rp#2024",  # VULNERABLE
        "email":       "svc_aircorp@corp.local",
        "groups":      ["CN=ServiceAccounts,DC=corp,DC=local"],
        "tier":        "Basic",
    },
    "demo": {
        "password":    "demo123",
        "username":    "demo",
        "name":        "Demo User",
        "department":  "Sales",
        "title":       "Sales Representative",
        "description": "Demo account for presentations",
        "email":       "demo@corp.local",
        "groups":      ["CN=Sales,DC=corp,DC=local"],
        "tier":        "Basic",
    },
}


# ── Local authentication ───────────────────────────────────────────────────────
def authenticate_local(username: str, password: str) -> dict | None:
    user = LOCAL_USERS.get(username)
    if user and user["password"] == password:
        print(f"[LOCAL AUTH SUCCESS] {username}")
        # Return same format as AD auth — minus the password field
        return {k: v for k, v in user.items() if k != "password"}
    print(f"[LOCAL AUTH FAILED] {username}")
    return None


# ── AD authentication ──────────────────────────────────────────────────────────
def authenticate_ad(username: str, password: str) -> dict | None:
    """
    Authenticate user against Active Directory.
    Returns user info dict if successful, None if failed.
    VULNERABLE: returns full AD attributes including department and description.
    """
    try:
        from ldap3 import Server, Connection, ALL, SUBTREE
        server  = Server(AD_SERVER, get_info=ALL)
        user_dn = f"{AD_DOMAIN}\\{username}"
        conn    = Connection(server, user=user_dn, password=password, auto_bind=True)
        if not conn.bound:
            print(f"[AD AUTH FAILED] {username}")
            return None
        print(f"[AD AUTH SUCCESS] {username}")
        conn.search(
            AD_BASE_DN,
            f"(sAMAccountName={username})",
            search_scope=SUBTREE,
            attributes=["sAMAccountName", "givenName", "sn",
                        "department", "title", "description",
                        "memberOf", "mail"]
        )
        if not conn.entries:
            return None
        entry = conn.entries[0]
        return {
            "username":    str(entry.sAMAccountName),
            "name":        f"{entry.givenName} {entry.sn}",
            "department":  str(entry.department),
            "title":       str(entry.title),
            "description": str(entry.description),
            "email":       str(entry.mail) if entry.mail else f"{username}@corp.local",
            "groups":      [str(g) for g in entry.memberOf] if entry.memberOf else [],
        }
    except ImportError:
        print("[AD AUTH] ldap3 not installed — falling back to local auth")
        return authenticate_local(username, password)
    except Exception as e:
        print(f"[AD AUTH ERROR]: {e}")
        return None


# ── Router ─────────────────────────────────────────────────────────────────────
def authenticate(username: str, password: str) -> dict | None:
    """
    Route to AD or local auth based on AUTH_MODE env var.
    If AD fails due to connectivity, automatically falls back to local.
    """
    if AUTH_MODE == "local":
        return authenticate_local(username, password)

    # Try AD first; fall back to local if unreachable
    result = authenticate_ad(username, password)
    if result is None and AUTH_MODE == "ad_with_fallback":
        print("[AUTH] AD unavailable — falling back to local users")
        return authenticate_local(username, password)
    return result


def is_staff(user_info: dict) -> bool:
    """Check if user is IT staff."""
    return user_info.get("department", "").lower() == "it"
