"""Rule-based PCIe protocol checker (simplified, educational subset of the spec)."""
from dataclasses import dataclass, asdict

NON_POSTED = {"MRd", "CfgRd0", "CfgRd1", "CfgWr0", "CfgWr1"}
POSTED = {"MWr", "Msg"}
COMPLETIONS = {"Cpl", "CplD"}
MAX_PAYLOAD_DW = 1024

# Simplified legal LTSSM transitions (subset of PCIe base spec state machine)
LEGAL_LTSSM = {
    "Detect.Quiet": {"Detect.Active"},
    "Detect.Active": {"Detect.Quiet", "Polling.Active"},
    "Polling.Active": {"Polling.Configuration", "Detect.Quiet"},
    "Polling.Configuration": {"Config.Linkwidth.Start", "Detect.Quiet"},
    "Config.Linkwidth.Start": {"Config.Linkwidth.Accept", "Detect.Quiet"},
    "Config.Linkwidth.Accept": {"Config.Lanenum.Wait", "Detect.Quiet"},
    "Config.Lanenum.Wait": {"Config.Lanenum.Accept", "Detect.Quiet"},
    "Config.Lanenum.Accept": {"Config.Complete", "Config.Linkwidth.Start", "Detect.Quiet"},
    "Config.Complete": {"Config.Idle", "Detect.Quiet"},
    "Config.Idle": {"L0", "Detect.Quiet"},
    "L0": {"L0s", "L1", "Recovery.RcvrLock"},
    "L0s": {"L0", "Recovery.RcvrLock"},
    "L1": {"Recovery.RcvrLock"},
    "Recovery.RcvrLock": {"Recovery.RcvrCfg", "Detect.Quiet"},
    "Recovery.RcvrCfg": {"Recovery.Idle", "Recovery.RcvrLock", "Detect.Quiet"},
    "Recovery.Idle": {"L0", "Config.Linkwidth.Start", "Detect.Quiet"},
}

SEVERITY = {"R01": "error", "R02": "error", "R03": "error", "R04": "error",
            "R05": "error", "R06": "warning", "R07": "error", "R08": "error"}


@dataclass
class Violation:
    rule_id: str
    severity: str
    time_ns: int
    line_no: int
    message: str

    def to_dict(self):
        return asdict(self)


def check(events, timeout_ns=50_000):
    v = []
    inflight = {}   # tag -> request event
    last_state = None

    def add(rule, ev, msg):
        v.append(Violation(rule, SEVERITY[rule], ev.time_ns, ev.line_no, msg))

    for ev in events:
        if ev.kind == "LTSSM":
            if last_state is not None and ev.src_state != last_state:
                add("R05", ev, f"LTSSM discontinuity: log says {ev.src_state} but previous state was {last_state}")
            elif ev.dst_state not in LEGAL_LTSSM.get(ev.src_state, set()):
                add("R05", ev, f"Illegal LTSSM transition {ev.src_state} -> {ev.dst_state}")
            last_state = ev.dst_state
            continue

        t, f = ev.tlp_type, ev.fields
        if t in NON_POSTED or t in POSTED:
            ln = f.get("len")
            if not isinstance(ln, int) or ln < 1 or ln > MAX_PAYLOAD_DW:
                add("R08", ev, f"{t} has invalid length {ln!r} (valid 1..{MAX_PAYLOAD_DW} DW)")
        if t in NON_POSTED:
            tag = f.get("tag")
            if tag in inflight:
                add("R02", ev, f"Tag {tag} reused while request from line {inflight[tag].line_no} is still outstanding")
            inflight[tag] = ev
        elif t in COMPLETIONS:
            tag = f.get("tag")
            req = inflight.pop(tag, None)
            if req is None:
                add("R01", ev, f"{t} with tag {tag} has no matching outstanding request")
                continue
            if t == "CplD" and f.get("status", "SC") == "SC" and f.get("len") != req.fields.get("len"):
                add("R03", ev, f"Completion length {f.get('len')} != request length {req.fields.get('len')} (tag {tag})")
            if ev.time_ns - req.time_ns > timeout_ns:
                add("R04", ev, f"Completion for tag {tag} arrived after {ev.time_ns - req.time_ns}ns (limit {timeout_ns}ns)")
            if f.get("status", "SC") in ("UR", "CA"):
                add("R06", ev, f"Completion returned error status {f['status']} for tag {tag}")

    for tag, req in inflight.items():
        v.append(Violation("R07", SEVERITY["R07"], req.time_ns, req.line_no,
                           f"{req.tlp_type} tag {tag} never received a completion before end of simulation"))
    return sorted(v, key=lambda x: x.time_ns)
