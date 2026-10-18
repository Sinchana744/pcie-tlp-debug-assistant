import argparse, json, os, glob
from .analyzer import analyze_many, summarize


def print_summary(s):
    print(f"\n=== Regression summary: {s['passed']}/{s['total']} passed, {s['failed']} failed ===")
    for rid, d in s["by_rule"].items():
        print(f"\n[{rid}] {d['title']}  x{d['count']}")
        print(f"  cause : {d['root_cause']}")
        print(f"  spec  : {d['spec_ref']}")
        print(f"  fix   : {d['suggested_fix']}")
        if d.get("llm_analysis"):
            print(f"  LLM   : {d['llm_analysis']}")
        for e in d["examples"]:
            print(f"    - {e}")


def main(argv=None):
    ap = argparse.ArgumentParser(prog="pcie_debug")
    sub = ap.add_subparsers(dest="cmd", required=True)
    a = sub.add_parser("analyze", help="analyze log files/dirs in parallel")
    a.add_argument("paths", nargs="+")
    a.add_argument("--out", default="results/report.json")
    a.add_argument("--workers", type=int, default=os.cpu_count())
    a.add_argument("--timeout-ns", type=int, default=50_000)
    a.add_argument("--llm", action="store_true", help="use Anthropic API for deeper explanations")
    s = sub.add_parser("summarize", help="merge JSON results (e.g. from Slurm array jobs)")
    s.add_argument("results_dir")
    s.add_argument("--llm", action="store_true")
    args = ap.parse_args(argv)

    if args.cmd == "analyze":
        runs = analyze_many(args.paths, args.workers, args.timeout_ns)
        os.makedirs(os.path.dirname(args.out) or ".", exist_ok=True)
        json.dump(runs, open(args.out, "w"), indent=2)
        print_summary(summarize(runs, args.llm))
        print(f"\nSaved: {args.out}")
    else:
        runs = []
        for f in sorted(glob.glob(os.path.join(args.results_dir, "*.json"))):
            if os.path.basename(f) != "summary.json":
                runs += json.load(open(f))
        s = summarize(runs, args.llm)
        json.dump(s, open(os.path.join(args.results_dir, "summary.json"), "w"), indent=2)
        print_summary(s)


if __name__ == "__main__":
    main()
