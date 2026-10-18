"""Generate synthetic PCIe logs with optional injected bugs (for demo & tests)."""
import argparse, os, random

BUGS = ["none", "orphan_cpl", "dup_tag", "len_mismatch", "timeout", "bad_ltssm", "ur_status", "lost_cpl", "bad_len"]
TRAIN = ["Detect.Quiet", "Detect.Active", "Polling.Active", "Polling.Configuration", "Config.Linkwidth.Start",
         "Config.Linkwidth.Accept", "Config.Lanenum.Wait", "Config.Lanenum.Accept", "Config.Complete", "Config.Idle", "L0"]


def gen(bug, rng):
    L, t = [], 100
    for a, b in zip(TRAIN, TRAIN[1:]):
        t += rng.randint(50, 500)
        if bug == "bad_ltssm" and b == "Config.Linkwidth.Start":
            L.append((t, f"[{t}ns] LTSSM {a} -> L0"))   # skipped link training states
            break
        L.append((t, f"[{t}ns] LTSSM {a} -> {b}"))
    t += 1000
    n = rng.randint(6, 12)
    bug_at = rng.randint(1, n - 1)
    for tag in range(n):
        ln = rng.choice([1, 2, 4, 8, 16])
        t += rng.randint(20, 200)
        L.append((t, f"[{t}ns] TX MRd addr=0x{rng.randrange(0, 0xFFFF, 4):x} len={ln} tag={tag}"))
        if bug == "dup_tag" and tag == bug_at:
            L.append((t + 5, f"[{t+5}ns] TX MRd addr=0x40 len=1 tag={tag}"))
        if bug == "bad_len" and tag == bug_at:
            L.append((t + 5, f"[{t+5}ns] TX MWr addr=0x80 len=0 tag=0"))
        if bug == "lost_cpl" and tag == bug_at:
            continue
        lat = 300 + rng.randint(0, 400)
        cl, status = ln, "SC"
        if bug == "len_mismatch" and tag == bug_at:
            cl = ln + 1
        if bug == "timeout" and tag == bug_at:
            lat = 80_000
        if bug == "ur_status" and tag == bug_at:
            status = "UR"
        L.append((t + lat, f"[{t+lat}ns] RX CplD tag={tag} len={cl} status={status}"))
        if bug == "orphan_cpl" and tag == bug_at:
            L.append((t + lat + 10, f"[{t+lat+10}ns] RX CplD tag=99 len=4 status=SC"))
    L.sort(key=lambda x: x[0])
    return "# synthetic PCIe log\n" + "\n".join(s for _, s in L) + "\n"


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="logs")
    ap.add_argument("--count", type=int, default=20)
    ap.add_argument("--seed", type=int, default=7)
    a = ap.parse_args()
    rng = random.Random(a.seed)
    os.makedirs(a.out, exist_ok=True)
    for i in range(a.count):
        bug = "none" if i % 3 == 0 else rng.choice(BUGS[1:])
        open(os.path.join(a.out, f"test_{i:03d}_{bug}.log"), "w").write(gen(bug, rng))
    print(f"Wrote {a.count} logs to {a.out}/")
