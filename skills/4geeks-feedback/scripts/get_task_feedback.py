#!/usr/bin/env python3
"""Fetch one authenticated student's task details and emit only minimized fields."""

import json
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

BASE = "https://breathecode.herokuapp.com"
TASKS_PATH = "/v1/assignment/user/me/task"
TIMEOUT_SECONDS = 20

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
        with urllib.request.urlopen(req, timeout=TIMEOUT_SECONDS) as response:
            status, body = response.status, response.read()
    except urllib.error.HTTPError as exc:
        return exc.code, None, "authentication_rejected" if exc.code in (401, 403) else "http_error"
    except (urllib.error.URLError, TimeoutError, OSError):
        return None, None, "network_error"
    try:
        return status, json.loads(body.decode("utf-8")), None
    except (UnicodeDecodeError, json.JSONDecodeError):
        return status, None, "unexpected_response"


def task_rows(payload):
    if isinstance(payload, list):
        return payload
    if isinstance(payload, dict) and isinstance(payload.get("results"), list):
        return payload["results"]
    return None


def cohort_id(row):
    cohort = row.get("cohort") if isinstance(row, dict) else None
    if isinstance(cohort, dict):
        return cohort.get("id")
    return row.get("cohort_id") if isinstance(row, dict) else None


def feedback_fields(detail):
    """Only surface explicit, known feedback/comment fields; omit arbitrary payloads."""
    aliases = ("feedback", "feedback_text", "review_feedback", "review_comment", "comment", "comments")
    output = {}
    for key in aliases:
        if key in detail:
            value = detail[key]
            if value is None:
                output[key] = None
            elif isinstance(value, (str, int, float, bool)):
                output[key] = str(value)[:2000] if isinstance(value, str) else value
            else:
                # Nested review objects may contain private payloads; expose only presence.
                output[key] = "present_non_scalar"
    if output:
        return output, "empty" if all(v in (None, "") for v in output.values()) else "available"
    return {}, "field_absent"


def emit(report, code):
    print(json.dumps(report, ensure_ascii=False, separators=(",", ":")))
    return code


def main(task_id_text, cohort_id_text):
    if not task_id_text.isdigit() or not cohort_id_text.isdigit():
        return emit({"complete": False, "error": "numeric_task_and_cohort_ids_required"}, 2)
    task_id, expected_cohort_id = int(task_id_text), int(cohort_id_text)
    token = load_token()
    if not token:
        return emit({"complete": False, "error": "credential_unavailable"}, 2)

    report = {
        "task_id": task_id,
        "expected_cohort_id": expected_cohort_id,
        "list_endpoint": TASKS_PATH,
        "detail_endpoint": f"{TASKS_PATH}/{task_id}",
        "http_list": [],
        "list_pages": 0,
        "http_detail": None,
        "ownership_verified_from_student_list": False,
        "cohort_verified": False,
        "complete": False,
    }
    offset = 0
    seen_signatures = set()
    listed = None
    while True:
        status, payload, error = request_json(
            TASKS_PATH, token, {"cohort": expected_cohort_id, "limit": 100, "offset": offset}
        )
        report["http_list"].append(status)
        report["list_pages"] += 1
        if error:
            del token
            report["error"] = error
            return emit(report, 1)
        rows = task_rows(payload)
        if rows is None:
            del token
            report["error"] = "unexpected_task_list_shape"
            return emit(report, 1)
        signature = tuple(str(row.get("id", "")) if isinstance(row, dict) else "" for row in rows)
        if rows and signature in seen_signatures:
            del token
            report["error"] = "pagination_repeated_page"
            return emit(report, 1)
        if rows:
            seen_signatures.add(signature)
        matches = [row for row in rows if isinstance(row, dict) and str(row.get("id")) == str(task_id)]
        if matches:
            if len(matches) != 1:
                del token
                report["error"] = "task_id_ambiguous_in_student_list"
                return emit(report, 1)
            listed = matches[0]
            break
        if len(rows) < 100:
            break
        offset += len(rows)
        if offset > 100000:
            del token
            report["error"] = "pagination_safety_limit"
            return emit(report, 1)

    if listed is None:
        del token
        report["error"] = "task_not_found_in_student_cohort_list"
        return emit(report, 1)
    actual_cohort_id = cohort_id(listed)
    report["ownership_verified_from_student_list"] = True
    report["cohort_verified"] = str(actual_cohort_id) == str(expected_cohort_id)
    report["listed_task_status"] = listed.get("task_status")
    report["listed_revision_status"] = listed.get("revision_status")
    if not report["cohort_verified"]:
        del token
        report["error"] = "cohort_mismatch"
        return emit(report, 1)

    status, detail, error = request_json(f"{TASKS_PATH}/{task_id}", token)
    del token
    report["http_detail"] = status
    if error:
        report["error"] = error
        return emit(report, 1)
    if not isinstance(detail, dict) or str(detail.get("id")) != str(task_id):
        report["error"] = "detail_id_mismatch_or_unexpected_shape"
        return emit(report, 1)
    detail_cohort_id = cohort_id(detail)
    if str(detail_cohort_id) != str(expected_cohort_id):
        report["error"] = "detail_cohort_mismatch"
        return emit(report, 1)

    feedback, feedback_state = feedback_fields(detail)
    report.update({
        "cohort_id": expected_cohort_id,
        "title": detail.get("title") if isinstance(detail.get("title"), str) else None,
        "task_type": detail.get("task_type"),
        "task_status": detail.get("task_status"),
        "revision_status": detail.get("revision_status"),
        "feedback_fields": feedback,
        "feedback_state": feedback_state,
        "grade_fields": {key: detail[key] for key in ("grade", "score", "rating") if key in detail and isinstance(detail[key], (str, int, float, bool, type(None)))},
        "complete": True,
    })
    return emit(report, 0)


if __name__ == "__main__":
    if len(sys.argv) != 3:
        sys.exit(emit({"complete": False, "error": "usage: get_task_feedback.py <task_id> <cohort_id>"}, 2))
    sys.exit(main(sys.argv[1], sys.argv[2]))
