#!/usr/bin/env python3
"""List the authenticated student's 4Geeks cohort enrollments, minimized."""

import json
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

BASE = "https://breathecode.herokuapp.com"
COHORT_ME_PATH = "/v1/admissions/academy/cohort/me"
USER_ME_PATH = "/v1/admissions/user/me"
TIMEOUT_SECONDS = 20

# Reuse the existing safe credential reader; never emit the token.
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "4geeks-conexion" / "scripts"))
from check_connection import load_token  # noqa: E402


def request_json(path, token):
    request = urllib.request.Request(
        BASE + path,
        headers={"Authorization": "Token " + token, "Accept": "application/json"},
        method="GET",
    )
    try:
        with urllib.request.urlopen(request, timeout=TIMEOUT_SECONDS) as response:
            status, body = response.status, response.read()
    except urllib.error.HTTPError as exc:
        return exc.code, None, "authentication_rejected" if exc.code in (401, 403) else "http_error"
    except (urllib.error.URLError, TimeoutError, OSError):
        return None, None, "network_error"
    try:
        return status, json.loads(body.decode("utf-8")), None
    except (UnicodeDecodeError, json.JSONDecodeError):
        return status, None, "unexpected_response"


def unwrap_cohort(enrollment):
    if not isinstance(enrollment, dict):
        return {}
    cohort = enrollment.get("cohort")
    return cohort if isinstance(cohort, dict) else enrollment


def minimal_enrollment(enrollment):
    """Copy only the requested cohort labels, enrollment status, and separate stage."""
    cohort = unwrap_cohort(enrollment)
    name = cohort.get("name")
    slug = cohort.get("slug")
    educational_status = enrollment.get("educational_status") if isinstance(enrollment, dict) else None
    stage = cohort.get("stage")
    return {
        "name": name if isinstance(name, str) and name.strip() else None,
        "slug": slug if isinstance(slug, str) and slug.strip() else None,
        "educational_status": educational_status if isinstance(educational_status, str) and educational_status.strip() else None,
        "stage": stage if isinstance(stage, str) and stage.strip() else None,
    }


def main():
    token = load_token()
    if not token:
        print(json.dumps({"complete": False, "error": "credential_unavailable"}))
        return 2

    initial_http, initial_payload, initial_error = request_json(COHORT_ME_PATH, token)
    report = {
        "endpoint_attempted": COHORT_ME_PATH,
        "http_initial": initial_http,
        "endpoint_used": None,
        "http_student": None,
        "fallback_reason": None,
        "complete": False,
    }

    cohort_rows = None
    if initial_http == 200 and initial_error is None:
        if isinstance(initial_payload, list):
            candidate_rows = initial_payload
            has_enrollment_status = all(
                isinstance(row, dict) and "educational_status" in row for row in candidate_rows
            )
        elif isinstance(initial_payload, dict) and isinstance(initial_payload.get("results"), list):
            candidate_rows = initial_payload["results"]
            has_enrollment_status = all(
                isinstance(row, dict) and "educational_status" in row for row in candidate_rows
            )
            if initial_payload.get("next"):
                has_enrollment_status = False
        else:
            candidate_rows = None
            has_enrollment_status = False
        if has_enrollment_status and candidate_rows:
            cohort_rows = candidate_rows
            source = COHORT_ME_PATH
        else:
            # Cohort objects alone do not prove enrollment educational_status.
            report["fallback_reason"] = "cohort_endpoint_missing_enrollment_status"
            status, payload, error = request_json(USER_ME_PATH, token)
            report["http_student"] = status
            report["endpoint_used"] = USER_ME_PATH
            if error:
                report["error"] = error
                del token
                print(json.dumps(report, ensure_ascii=False, separators=(",", ":")))
                return 1
            if not isinstance(payload, dict) or not isinstance(payload.get("cohorts"), list):
                report["error"] = "unexpected_cohorts_shape"
                del token
                print(json.dumps(report, ensure_ascii=False, separators=(",", ":")))
                return 1
            cohort_rows = payload["cohorts"]
            source = USER_ME_PATH
    elif initial_http in (401, 403):
        report["fallback_reason"] = "student_endpoint_after_access_denied"
        status, payload, error = request_json(USER_ME_PATH, token)
        report["http_student"] = status
        report["endpoint_used"] = USER_ME_PATH
        if error:
            report["error"] = error
            del token
            print(json.dumps(report, ensure_ascii=False, separators=(",", ":")))
            return 1
        source = USER_ME_PATH
        if not isinstance(payload, dict) or not isinstance(payload.get("cohorts"), list):
            report["error"] = "unexpected_cohorts_shape"
            del token
            print(json.dumps(report, ensure_ascii=False, separators=(",", ":")))
            return 1
        cohort_rows = payload["cohorts"]
    else:
        report["endpoint_used"] = COHORT_ME_PATH
        report["error"] = initial_error or "unexpected_http_status"
        del token
        print(json.dumps(report, ensure_ascii=False, separators=(",", ":")))
        return 1

    del token
    report["endpoint_used"] = source
    report["enrollments"] = [minimal_enrollment(item) for item in cohort_rows]
    report["enrollment_count"] = len(cohort_rows)
    report["multiple_enrollments"] = len(cohort_rows) > 1
    report["complete"] = True
    print(json.dumps(report, ensure_ascii=False, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    sys.exit(main())
