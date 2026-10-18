import os
from concurrent.futures import ProcessPoolExecutor
from collections import defaultdict
from .parser import parse_file
from .rules import check
from .explain import explain_rule


def analyze_file(path, timeout_ns=50_000):
    events, unparsed = parse_file(path)
    violations = [x.to_dict() for x in check(events, timeout_ns)]
    return {"file": os.path.basename(path), "events": len(events), "unparsed_lines": len(unparsed),
            "status": "FAIL" if any(x["severity"] == "error" for x in violations) else "PASS",
            "violations": violations}


def collect_logs(paths):
    files = []
    for p in paths:
        if os.path.isdir(p):
            files += sorted(os.path.join(p, f) for f in os.listdir(p) if f.endswith(".log"))
        else:
            files.append(p)
    return files


def analyze_many(paths, workers=None, timeout_ns=50_000):
    files = collect_logs(paths)
    with ProcessPoolExecutor(max_workers=workers) as ex:
        return list(ex.map(analyze_file, files, [timeout_ns] * len(files)))


def summarize(runs, use_llm=False):
    by_rule = defaultdict(list)
    for r in runs:
        for v in r["violations"]:
            by_rule[v["rule_id"]].append(f"{r['file']}:{v['line_no']} {v['message']}")
    return {
        "total": len(runs),
        "passed": sum(r["status"] == "PASS" for r in runs),
        "failed": sum(r["status"] == "FAIL" for r in runs),
        "by_rule": {rid: {"count": len(ex), "examples": ex[:3], **explain_rule(rid, ex, use_llm)}
                    for rid, ex in sorted(by_rule.items())},
    }
