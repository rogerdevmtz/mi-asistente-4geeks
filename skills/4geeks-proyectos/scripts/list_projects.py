#!/usr/bin/env python3
"""List all student projects for an exact cohort slug; emit a privacy-minimized report."""

import json
import sys
import urllib.error
import urllib.parse
import urllib.request

from pathlib import Path


BASE = "https://breathecode.herokuapp.com"
COHORTS_PATH = "/v1/admissions/academy/cohort/me"
TASKS_PATH = "/v1/assignment/user/me/task"
PAGE_SIZE = 100
TIMEOUT = 20

# Reuse the existing safe credential reader without copying any secret to stdout.
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "4geeks-conexion" / "scripts"))
from check_connection import load_token  # noqa: E402


def request_json(path, token, params=None):
    query = urllib.parse.urlencode(params or {})
    url = BASE + path + ("?" + query if query else "")
    req = urllib.request.Request(
        url,
        headers={"Authorization": "Token " + token, "Accept": "application/json"},
        method="GET",
    )
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT) as response:
            status = response.status
            body = response.read()
    except urllib.error.HTTPError as exc:
        return exc.code, None, "authentication_rejected" if exc.code in (401, 403) else "http_error"
    except (urllib.error.URLError, TimeoutError, OSError):
        return None, None, "network_error"
    try:
        return status, json.loads(body.decode("utf-8")), None
    except (UnicodeDecodeError, json.JSONDecodeError):
        return status, None, "unexpected_response"


def rows_from(payload):
    if isinstance(payload, list):
        return payload, None
    if isinstance(payload, dict):
        rows = payload.get("results")
        if isinstance(rows, list):
            return rows, payload
    return None, None


def query_matches_next(next_value, cohort_id):
    """Only follow server pagination if its query retains both required filters."""
    try:
        query = urllib.parse.parse_qs(urllib.parse.urlparse(next_value).query)
        return (query.get("task_type") == ["PROJECT"] and
                query.get("cohort") == [str(cohort_id)])
    except (TypeError, ValueError):
        return False


def cohort_info(row):
    if not isinstance(row, dict):
        return None, None
    cohort = row.get("cohort")
    if isinstance(cohort, dict):
        return cohort.get("slug"), cohort.get("id")
    return row.get("cohort_slug"), cohort if isinstance(cohort, (int, str)) else row.get("cohort_id")


def cohort_id_from_user(user, slug):
    """Fallback source documented by the reference: current user's cohort list."""
    matches = []
    if not isinstance(user, dict) or not isinstance(user.get("cohorts"), list):
        return matches
    for enrollment in user["cohorts"]:
        if isinstance(enrollment, dict):
            cohort = enrollment.get("cohort")
            if isinstance(cohort, dict) and cohort.get("slug") == slug and cohort.get("id") not in (None, ""):
                matches.append(cohort["id"])
    return list(dict.fromkeys(matches))


def minimal_project(row):
    if not isinstance(row, dict):
        return {"name": "(nombre no disponible)", "status": "UNKNOWN", "id": None}
    asset = row.get("task") or row.get("asset")
    title = None
    if isinstance(asset, dict):
        title = asset.get("title") or asset.get("name")
    title = title or row.get("title") or row.get("name")
    task_id = row.get("id") or row.get("task_id")
    safe_name = str(title)[:180] if isinstance(title, (str, int)) and str(title).strip() else "(nombre no disponible)"
    task_status = str(row.get("task_status") or row.get("status") or "UNKNOWN").upper()
    revision_status = str(row.get("revision_status") or "").upper()
    if revision_status in ("APPROVED", "REJECTED"):
        status = revision_status
    elif task_status in ("PENDING", "DONE") and revision_status in ("", "PENDING"):
        status = task_status
    else:
        status = "UNKNOWN"
    return {
        "name": safe_name,
        "status": status,
        "task_status": task_status,
        "revision_status": revision_status or None,
        "id": task_id if isinstance(task_id, (int, str)) else None,
    }


def emit(report, exit_code):
    print(json.dumps(report, ensure_ascii=False, separators=(",", ":")))
    return exit_code


def main(slug):
    token = load_token()
    if not token:
        return emit({"error": "credential_unavailable", "complete": False}, 2)

    cohort_http, payload, err = request_json(COHORTS_PATH, token)
    cohort_source = COHORTS_PATH
    if cohort_http in (401, 403):
        # The documented authenticated user endpoint also carries the student's cohort list.
        user_http, user_payload, user_err = request_json("/v1/admissions/user/me", token)
        cohort_http = user_http
        err = user_err
        cohort_source = "/v1/admissions/user/me"
        ids = cohort_id_from_user(user_payload, slug)
    else:
        if err:
            del token
            return emit({"error": err, "http_status": cohort_http, "endpoint": COHORTS_PATH, "complete": False}, 1)
        cohorts, _ = rows_from(payload)
        if cohorts is None:
            del token
            return emit({"error": "unexpected_cohorts_shape", "http_status": cohort_http, "endpoint": COHORTS_PATH, "complete": False}, 1)
        matching = []
        for enrollment in cohorts:
            found_slug, cohort_id = cohort_info(enrollment)
            if found_slug == slug and cohort_id not in (None, ""):
                matching.append(cohort_id)
        ids = list(dict.fromkeys(matching))
    if err:
        del token
        return emit({"error": err, "http_status": cohort_http, "endpoint": cohort_source, "complete": False}, 1)
    if len(ids) != 1:
        del token
        return emit({
            "http_status_cohorts": cohort_http,
            "cohort_source": cohort_source,
            "requested_slug": slug,
            "slug_match_count": len(ids),
            "error": "cohort_not_found_or_ambiguous",
            "complete": False,
        }, 1)
    cohort_id = ids[0]

    report = {
        "requested_slug": slug,
        "cohort_id": cohort_id,
        "http_status_cohorts": cohort_http,
        "cohort_source": cohort_source,
        "http_status_tasks": [],
        "filter_applied": None,
        "pagination_complete": False,
        "cohort_filter_verified_from_rows": None,
        "complete": False,
        "projects": [],
        "totals": {"PENDING": 0, "DONE": 0, "APPROVED": 0, "REJECTED": 0, "UNKNOWN": 0},
        "error": None,
    }
    offset = 0
    seen_page_signatures = set()
    row_cohort_evidence = []
    while True:
        query = {"task_type": "PROJECT", "cohort": cohort_id, "limit": PAGE_SIZE, "offset": offset}
        report["filter_applied"] = {"task_type": "PROJECT", "cohort": cohort_id}
        status, data, err = request_json(TASKS_PATH, token, query)
        report["http_status_tasks"].append(status)
        if err:
            report["error"] = err
            break
        rows, page_meta = rows_from(data)
        if rows is None:
            report["error"] = "unexpected_tasks_shape"
            break

        signature = tuple(
            (str(r.get("id", "")), str(r.get("task_status", r.get("status", ""))))
            if isinstance(r, dict) else ("", "") for r in rows
        )
        if rows and signature in seen_page_signatures:
            report["error"] = "pagination_repeated_page"
            break
        if rows:
            seen_page_signatures.add(signature)

        for row in rows:
            found_slug, found_id = cohort_info(row)
            if found_slug is not None or found_id is not None:
                row_cohort_evidence.append(found_slug == slug and str(found_id) == str(cohort_id))
            if not isinstance(row, dict) or str(row.get("task_type", "")).upper() != "PROJECT":
                report["error"] = "non_project_in_filtered_results"
                break
            report["projects"].append(minimal_project(row))
        if report["error"]:
            break

        # If the API provides next, follow only offsets on the same verified filter.
        next_value = page_meta.get("next") if isinstance(page_meta, dict) else None
        if next_value:
            if not rows:
                report["error"] = "pagination_inconsistent"
                break
            if not query_matches_next(next_value, cohort_id):
                report["error"] = "pagination_filter_not_preserved"
                break
            offset += len(rows)
            continue
        if len(rows) < PAGE_SIZE:
            report["pagination_complete"] = True
            break
        offset += len(rows)

        if offset > 100000:
            report["error"] = "pagination_safety_limit"
            break

    del token
    if row_cohort_evidence:
        report["cohort_filter_verified_from_rows"] = all(row_cohort_evidence)
    else:
        # Filter is evidenced by the actual request parameter; rows omit cohort metadata.
        report["cohort_filter_verified_from_rows"] = None

    for project in report["projects"]:
        status = project["status"]
        if status not in report["totals"] or status == "UNKNOWN":
            project["status"] = "UNKNOWN" if status == "UNKNOWN" else status
            report["totals"]["UNKNOWN"] += 1
        else:
            report["totals"][status] += 1

    no_conflict = report["cohort_filter_verified_from_rows"] is not False
    report["complete"] = bool(report["pagination_complete"] and not report["error"] and no_conflict)
    if not no_conflict and not report["error"]:
        report["error"] = "cohort_mismatch_in_rows"
    return emit(report, 0 if report["complete"] else 1)


if __name__ == "__main__":
    if len(sys.argv) != 2 or not sys.argv[1].strip():
        print(json.dumps({"error": "usage: list_projects.py <cohort-slug>", "complete": False}))
        sys.exit(2)
    sys.exit(main(sys.argv[1].strip()))
