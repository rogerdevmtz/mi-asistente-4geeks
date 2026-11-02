#!/usr/bin/env python3
"""Check the authenticated 4Geeks student endpoint; print only redacted status."""

import json
import os
import re
import sys
import urllib.error
import urllib.request


ENV_FILE = "/root/.openclaw/.env"
URL = "https://breathecode.herokuapp.com/v1/admissions/user/me"
TIMEOUT_SECONDS = 15


def load_token():
    """Read only the named key, without printing or exporting the env file."""
    token = os.environ.get("FOURGEEKS_STUDENT_TOKEN")
    if token:
        return token.strip().strip("\"'")
    try:
        with open(ENV_FILE, "r", encoding="utf-8") as env_file:
            for line in env_file:
                match = re.match(r"^\s*FOURGEEKS_STUDENT_TOKEN\s*=\s*(.*?)\s*$", line)
                if match:
                    return match.group(1).strip().strip("\"'")
    except OSError:
        return ""
    return ""


def has_identity(user):
    """Return only whether a plausible current-user identity is present."""
    if not isinstance(user, dict):
        return False
    # API contract describes a user object with an identifier and profile data.
    return any(user.get(key) not in (None, "") for key in ("id", "user", "first_name", "name"))


def emit(status=None, session_valid=False, identity_verified=False, error=None):
    result = {
        "endpoint": "/v1/admissions/user/me",
        "http_status": status,
        "session_valid": bool(session_valid),
        "identity_verified": bool(identity_verified),
    }
    if error:
        result["error"] = error
    print(json.dumps(result, ensure_ascii=True))


def main():
    token = load_token()
    if not token:
        emit(error="credential_unavailable")
        return 2

    request = urllib.request.Request(
        URL,
        headers={"Authorization": "Token " + token, "Accept": "application/json"},
        method="GET",
    )
    # Drop the local reference before handling/printing any result.
    del token
    try:
        with urllib.request.urlopen(request, timeout=TIMEOUT_SECONDS) as response:
            status = response.status
            if status != 200:
                emit(status=status, error="unexpected_http_status")
                return 1
            try:
                user = json.loads(response.read().decode("utf-8"))
            except (UnicodeDecodeError, json.JSONDecodeError):
                emit(status=status, error="unexpected_response")
                return 1
    except urllib.error.HTTPError as exc:
        # Do not read or expose the response body.
        emit(status=exc.code, error="authentication_rejected" if exc.code in (401, 403) else "http_error")
        return 1
    except (urllib.error.URLError, TimeoutError, OSError):
        emit(error="network_error")
        return 1

    verified = has_identity(user)
    del user
    emit(status=200, session_valid=verified, identity_verified=verified,
         error=None if verified else "identity_not_verifiable")
    return 0 if verified else 1


if __name__ == "__main__":
    sys.exit(main())
