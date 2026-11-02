#!/usr/bin/env python3
"""Read and classify all assigned work for a 4Geeks macro-cohort (and linked modules)."""
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
DATE_FIELDS = ("due_date", "deadline", "expires_at")
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
    req = urllib.request.Request(url, headers={"Authorization": "Token " + token, "Accept": "application/json"}, method="GET")
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT) as response:
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
    if isinstance(value, dict):
        return value.get("id")
    return value


def resolve_scope(user, slug, mode):
    enrollments = user.get("cohorts") if isinstance(user, dict) else None
    if not isinstance(enrollments, list):
        return None, "unexpected_cohorts_shape"
    matches = [e for e in enrollments if cohort_object(e).get("slug") == slug]
    ids = list(dict.fromkeys(id_value(cohort_object(e).get("id")) for e in matches if id_value(cohort_object(e).get("id")) not in (None, "")))
    if len(ids) != 1:
        return None, "cohort_not_found_or_ambiguous"
    macro_id = ids[0]
    selected = {str(macro_id)}
    if mode == "course":
        for enrollment in enrollments:
            cohort = cohort_object(enrollment)
            # The source link may be serialized on the enrollment or nested cohort object.
            source = id_value(enrollment.get("source_macro_cohort")) if isinstance(enrollment, dict) else None
            if source is None:
                source = id_value(cohort.get("source_macro_cohort"))
            if str(source) == str(macro_id) and id_value(cohort.get("id")) not in (None, ""):
                selected.add(str(id_value(cohort.get("id"))))
    return {"macro_id": macro_id, "cohort_ids": sorted(selected, key=lambda x: (not x.isdigit(), int(x) if x.isdigit() else x)), "module_count": len(selected) - 1}, None


def result_rows(data):
    if isinstance(data, list):
        return data, None
    if isinstance(data, dict) and isinstance(data.get("results"), list):
        return data["results"], data
    return None, None


def safe_name(row):
    task = row.get("task") or row.get("asset")
    title = task.get("title") or task.get("name") if isinstance(task, dict) else None
    title = title or row.get("title") or row.get("name")
    if isinstance(title, (str, int)) and str(title).strip():
        return str(title).strip()[:180]
    return "(nombre no disponible)"


def normalized(value):
    return str(value).upper() if value not in (None, "") else ""


def classify(task_status, revision_status):
    ts, rs = normalized(task_status), normalized(revision_status)
    if rs == "REJECTED":
        return "corrections"
    if rs == "APPROVED":
        return "approved"
    if ts == "PENDING" and rs in ("", "PENDING"):
        return "to_do"
    if ts == "DONE" and rs in ("", "PENDING"):
        return "waiting_review"
    return "unclassified"


def deadline(row):
    for obj in (row, row.get("task"), row.get("asset")):
        if isinstance(obj, dict):
            for key in DATE_FIELDS:
                value = obj.get(key)
                if isinstance(value, (str, int, float)) and str(value).strip():
                    return {"field": key, "value": str(value)[:64]}
    return None


def row_cohort_ids(row):
    found = set()
    for candidate in (row.get("cohort"), (row.get("task") or {}).get("cohort") if isinstance(row.get("task"), dict) else None):
        if isinstance(candidate, dict) and candidate.get("id") is not None:
            found.add(str(candidate["id"]))
        elif isinstance(candidate, (str, int)):
            found.add(str(candidate))
    if row.get("cohort_id") is not None:
        found.add(str(row["cohort_id"]))
    return found


def main(slug, mode):
    token = load_token()
    if not token:
        print(json.dumps({"complete": False, "error": "credential_unavailable"}))
        return 2
    user_status, user, error = request_json(USER_PATH, token)
    report = {"requested_slug": slug, "scope_mode": mode, "http_user": user_status, "endpoint_user": USER_PATH,
              "http_tasks": [], "endpoint_tasks": TASKS_PATH, "complete": False}
    if error:
        report["error"] = error
        del token
        print(json.dumps(report, ensure_ascii=False)); return 1
    scope, error = resolve_scope(user, slug, mode)
    del user
    if error:
        report["error"] = error
        del token
        print(json.dumps(report, ensure_ascii=False)); return 1
    report.update({"macro_cohort_id": scope["macro_id"], "cohort_ids": scope["cohort_ids"], "linked_module_count": scope["module_count"]})
    records, seen, offsets = [], set(), set()
    next_url = None
    offset = 0
    cohort_evidence = []
    while True:
        if offset in offsets:
            report["error"] = "pagination_no_progress"; break
        offsets.add(offset)
        params = {"cohort": ",".join(scope["cohort_ids"]), "limit": PAGE_SIZE, "offset": offset}
        status, data, error = request_json(TASKS_PATH, token, params=params if not next_url else None, url=next_url)
        report["http_tasks"].append(status)
        if error:
            report["error"] = error; break
        rows, meta = result_rows(data)
        if rows is None:
            report["error"] = "unexpected_tasks_shape"; break
        signature = tuple((str(r.get("id", "")), normalized(r.get("task_status")), normalized(r.get("revision_status"))) if isinstance(r, dict) else ("", "", "") for r in rows)
        if rows and signature in seen:
            report["error"] = "pagination_repeated_page"; break
        if rows: seen.add(signature)
        invalid = False
        for row in rows:
            if not isinstance(row, dict):
                report["error"] = "unexpected_task_record"; invalid = True; break
            task_type = normalized(row.get("task_type")) or "UNKNOWN"
            cohorts = row_cohort_ids(row)
            if cohorts:
                cohort_evidence.append(bool(cohorts.intersection(scope["cohort_ids"])))
                if not cohorts.intersection(scope["cohort_ids"]):
                    report["error"] = "cohort_mismatch_in_rows"; invalid = True; break
            ts, rs = row.get("task_status"), row.get("revision_status")
            item = {"name": safe_name(row), "task_type": task_type,
                    "cohort_ids": sorted(cohorts.intersection(scope["cohort_ids"])) if cohorts else [],
                    "task_status": normalized(ts) or None, "revision_status": normalized(rs) or None,
                    "category": classify(ts, rs)}
            due = deadline(row)
            if due: item["deadline"] = due
            records.append(item)
        if invalid: break
        next_value = meta.get("next") if isinstance(meta, dict) else None
        if next_value:
            next_url = urllib.parse.urljoin(BASE, str(next_value))
            # Validate that pagination retains precisely the assigned-work cohort filter.
            q = urllib.parse.parse_qs(urllib.parse.urlparse(next_url).query)
            if q.get("cohort") != [",".join(scope["cohort_ids"])]:
                report["error"] = "pagination_filter_not_preserved"; break
            offset += len(rows)
            continue
        next_url = None
        if len(rows) < PAGE_SIZE:
            report["pagination_complete"] = True; break
        offset += len(rows)
    del token
    totals = {k: 0 for k in ("to_do", "corrections", "waiting_review", "approved", "unclassified")}
    by_type = {}
    for item in records:
        totals[item["category"]] += 1
        by_type.setdefault(item["task_type"], {k: 0 for k in totals})[item["category"]] += 1
    report.update({"filter_cohort_ids": scope["cohort_ids"], "cohort_membership_verified_from_rows": all(cohort_evidence) if cohort_evidence else None,
                   "pagination_complete": report.get("pagination_complete", False), "totals": totals,
                   "totals_by_task_type": by_type, "work": records,
                   "deadline_count": sum("deadline" in x for x in records),
                   "next_actions": {"to_do": "Completar y entregar", "corrections": "Corregir y volver a entregar",
                                    "waiting_review": "Esperar la revisión; no contar como pendiente",
                                    "approved": "Ninguna: ya aprobado", "unclassified": "Revisar estado con 4Geeks"}})
    report["complete"] = bool(report.get("pagination_complete") and not report.get("error") and not (False in cohort_evidence))
    print(json.dumps(report, ensure_ascii=False, separators=(",", ":")))
    return 0 if report["complete"] else 1


if __name__ == "__main__":
    if len(sys.argv) not in (2, 3) or not sys.argv[1].strip() or (len(sys.argv) == 3 and sys.argv[2] not in ("macro", "course")):
        print(json.dumps({"error": "usage: list_pending_work.py <cohort-slug> [macro|course]", "complete": False}))
        sys.exit(2)
    sys.exit(main(sys.argv[1].strip(), sys.argv[2] if len(sys.argv) == 3 else "course"))
