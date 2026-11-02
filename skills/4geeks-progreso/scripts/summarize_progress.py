#!/usr/bin/env python3
"""Aggregate authenticated student task statuses for a macro-cohort or linked course."""
import json
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

BASE = "https://breathecode.herokuapp.com"
USER_PATH = "/v1/admissions/user/me"
TASKS_PATH = "/v1/assignment/user/me/task"
PAGE_SIZE = 100
TIMEOUT = 20
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "4geeks-conexion" / "scripts"))
from check_connection import load_token  # noqa: E402


def request_json(path, token, params=None, url=None):
    if url:
        parsed = urllib.parse.urlparse(url)
        if parsed.scheme != "https" or parsed.netloc != "breathecode.herokuapp.com" or parsed.path != path:
            return None, None, "unsafe_pagination_url"
        url = urllib.parse.urlunparse(parsed)
    else:
        url = BASE + path + ("?" + urllib.parse.urlencode(params or {}, doseq=True) if params else "")
    request = urllib.request.Request(url, headers={"Authorization": "Token " + token, "Accept": "application/json"}, method="GET")
    try:
        with urllib.request.urlopen(request, timeout=TIMEOUT) as response:
            status, body = response.status, response.read()
    except urllib.error.HTTPError as exc:
        return exc.code, None, "authentication_rejected" if exc.code in (401, 403) else "http_error"
    except (urllib.error.URLError, TimeoutError, OSError):
        return None, None, "network_error"
    try:
        return status, json.loads(body.decode("utf-8")), None
    except (UnicodeDecodeError, json.JSONDecodeError):
        return status, None, "unexpected_response"


def cohort_object(enrollment):
    if not isinstance(enrollment, dict):
        return {}
    cohort = enrollment.get("cohort")
    return cohort if isinstance(cohort, dict) else enrollment


def id_value(value):
    return value.get("id") if isinstance(value, dict) else value


def resolve_scope(user, slug, mode):
    enrollments = user.get("cohorts") if isinstance(user, dict) else None
    if not isinstance(enrollments, list):
        return None, "unexpected_cohorts_shape"
    matches = [e for e in enrollments if cohort_object(e).get("slug") == slug]
    ids = list(dict.fromkeys(id_value(cohort_object(e).get("id")) for e in matches
                             if id_value(cohort_object(e).get("id")) not in (None, "")))
    if len(ids) != 1:
        return None, "cohort_not_found_or_ambiguous"
    macro_id = ids[0]
    selected = {str(macro_id)}
    if mode == "course":
        for enrollment in enrollments:
            cohort = cohort_object(enrollment)
            source = id_value(enrollment.get("source_macro_cohort")) if isinstance(enrollment, dict) else None
            if source is None:
                source = id_value(cohort.get("source_macro_cohort"))
            cohort_id = id_value(cohort.get("id"))
            if str(source) == str(macro_id) and cohort_id not in (None, ""):
                selected.add(str(cohort_id))
    ordered = sorted(selected, key=lambda x: (not x.isdigit(), int(x) if x.isdigit() else x))
    return {"macro_id": macro_id, "cohort_ids": ordered}, None


def rows_from(payload):
    if isinstance(payload, list):
        return payload, None
    if isinstance(payload, dict) and isinstance(payload.get("results"), list):
        return payload["results"], payload
    return None, None


def row_cohort_ids(row):
    found = set()
    for candidate in (row.get("cohort"), row.get("cohort_id")):
        if isinstance(candidate, dict) and candidate.get("id") is not None:
            found.add(str(candidate["id"]))
        elif isinstance(candidate, (str, int)):
            found.add(str(candidate))
    nested = row.get("task")
    if isinstance(nested, dict):
        cohort = nested.get("cohort")
        if isinstance(cohort, dict) and cohort.get("id") is not None:
            found.add(str(cohort["id"]))
        elif isinstance(cohort, (str, int)):
            found.add(str(cohort))
    return found


def increment(mapping, key):
    mapping[key] = mapping.get(key, 0) + 1


def main(slug, mode):
    token = load_token()
    if not token:
        print(json.dumps({"complete": False, "error": "credential_unavailable"}))
        return 2

    user_http, user, error = request_json(USER_PATH, token)
    report = {"requested_slug": slug, "scope_mode": mode, "endpoint_user": USER_PATH,
              "http_user": user_http, "endpoint_tasks": TASKS_PATH, "http_tasks": [], "complete": False}
    if error:
        report["error"] = error
        del token
        print(json.dumps(report)); return 1
    scope, error = resolve_scope(user, slug, mode)
    del user
    if error:
        report["error"] = error
        del token
        print(json.dumps(report)); return 1
    report.update({"macro_cohort_id": scope["macro_id"], "cohort_ids": scope["cohort_ids"],
                   "linked_module_count": len(scope["cohort_ids"]) - 1})

    total = 0
    task_done = 0
    revision_approved = 0
    task_status_counts = {}
    revision_status_counts = {}
    by_type = {}
    seen_pages = set()
    seen_offsets = set()
    offset = 0
    next_url = None
    cohort_verified = True
    cohort_rows = 0
    while True:
        if offset in seen_offsets:
            report["error"] = "pagination_no_progress"
            break
        seen_offsets.add(offset)
        params = {"cohort": ",".join(scope["cohort_ids"]), "limit": PAGE_SIZE, "offset": offset}
        status, payload, error = request_json(TASKS_PATH, token, params=params if next_url is None else None, url=next_url)
        report["http_tasks"].append(status)
        if error:
            report["error"] = error
            break
        rows, meta = rows_from(payload)
        if rows is None:
            report["error"] = "unexpected_tasks_shape"
            break
        signature = tuple((str(row.get("id", "")), str(row.get("task_status", "")),
                           str(row.get("revision_status", ""))) if isinstance(row, dict) else ("", "", "") for row in rows)
        if rows and signature in seen_pages:
            report["error"] = "pagination_repeated_page"
            break
        if rows:
            seen_pages.add(signature)
        invalid = False
        for row in rows:
            if not isinstance(row, dict):
                report["error"] = "unexpected_task_record"
                invalid = True
                break
            cohorts = row_cohort_ids(row)
            if not cohorts or not cohorts.intersection(scope["cohort_ids"]):
                cohort_verified = False
                report["error"] = "cohort_missing_or_mismatch_in_rows"
                invalid = True
                break
            cohort_rows += 1
            task_type = str(row.get("task_type") or "UNKNOWN").upper()
            task_status = str(row.get("task_status") or "MISSING").upper()
            revision_status = str(row.get("revision_status") or "MISSING").upper()
            total += 1
            increment(task_status_counts, task_status)
            increment(revision_status_counts, revision_status)
            typed = by_type.setdefault(task_type, {"total": 0, "task_status": {}, "revision_status": {},
                                                   "completed_by_me": 0, "approved_by_review": 0})
            typed["total"] += 1
            increment(typed["task_status"], task_status)
            increment(typed["revision_status"], revision_status)
            if task_status == "DONE":
                task_done += 1
                typed["completed_by_me"] += 1
            if revision_status == "APPROVED":
                revision_approved += 1
                typed["approved_by_review"] += 1
        if invalid:
            break
        next_value = meta.get("next") if isinstance(meta, dict) else None
        if next_value:
            next_url = urllib.parse.urljoin(BASE, str(next_value))
            parsed = urllib.parse.urlparse(next_url)
            query = urllib.parse.parse_qs(parsed.query)
            if (parsed.scheme != "https" or parsed.netloc != "breathecode.herokuapp.com" or parsed.path != TASKS_PATH
                    or query.get("cohort") != [",".join(scope["cohort_ids"]) ]):
                report["error"] = "pagination_filter_not_preserved"
                break
            offset += len(rows)
            continue
        next_url = None
        if len(rows) < PAGE_SIZE:
            report["pagination_complete"] = True
            break
        offset += len(rows)
    del token

    def metric(numerator):
        return {"numerator": numerator, "denominator": total,
                "percent": round(100 * numerator / total, 1) if total else None,
                "formula": "100 × numerador / denominador", "is_official_4geeks_metric": False}

    report.update({"denominator_definition": "registros de asignación del estudiante en los cohort IDs incluidos; cada registro cuenta una vez",
                   "total_assignments": total, "task_status_counts": task_status_counts,
                   "revision_status_counts": revision_status_counts,
                   "completed_by_me": metric(task_done), "approved_by_review": metric(revision_approved),
                   "by_task_type": by_type, "cohort_membership_verified_from_rows": cohort_verified,
                   "cohort_rows_verified": cohort_rows, "pagination_complete": report.get("pagination_complete", False)})
    report["complete"] = bool(report.get("pagination_complete") and not report.get("error") and cohort_verified)
    print(json.dumps(report, ensure_ascii=False, separators=(",", ":")))
    return 0 if report["complete"] else 1


if __name__ == "__main__":
    if len(sys.argv) not in (2, 3) or not sys.argv[1].strip() or (len(sys.argv) == 3 and sys.argv[2] not in ("macro", "course")):
        print(json.dumps({"error": "usage: summarize_progress.py <cohort-slug> [macro|course]", "complete": False}))
        sys.exit(2)
    sys.exit(main(sys.argv[1].strip(), sys.argv[2] if len(sys.argv) == 3 else "course"))
