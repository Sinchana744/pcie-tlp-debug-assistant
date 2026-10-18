"""Parse PCIe-style simulation logs into structured events.

Log format (one event per line):
  [1200ns] TX MRd addr=0x1000 len=4 tag=3
  [1800ns] RX CplD tag=3 len=4 status=SC
  [ 500ns] LTSSM Detect.Quiet -> Detect.Active
Lines starting with '#' are comments.
"""
import re
from dataclasses import dataclass, field
from typing import Optional

TLP_RE = re.compile(r"^\[\s*(?P<t>\d+)ns\]\s+(?P<dir>TX|RX)\s+(?P<type>\w+)\s*(?P<rest>.*)$")
LTSSM_RE = re.compile(r"^\[\s*(?P<t>\d+)ns\]\s+LTSSM\s+(?P<a>\S+)\s*->\s*(?P<b>\S+)")
KV_RE = re.compile(r"(\w+)=(\S+)")


@dataclass
class Event:
    line_no: int
    time_ns: int
    kind: str                       # "TLP" or "LTSSM"
    direction: Optional[str] = None
    tlp_type: Optional[str] = None
    fields: dict = field(default_factory=dict)
    src_state: Optional[str] = None
    dst_state: Optional[str] = None
    raw: str = ""


def _num(v: str):
    try:
        return int(v, 0)
    except ValueError:
        return v


def parse_lines(lines):
    events, unparsed = [], []
    for i, line in enumerate(lines, 1):
        s = line.strip()
        if not s or s.startswith("#"):
            continue
        m = LTSSM_RE.match(s)
        if m:
            events.append(Event(i, int(m["t"]), "LTSSM", src_state=m["a"], dst_state=m["b"], raw=s))
            continue
        m = TLP_RE.match(s)
        if m:
            f = {k: _num(v) if k != "status" else v for k, v in KV_RE.findall(m["rest"])}
            events.append(Event(i, int(m["t"]), "TLP", m["dir"], m["type"], f, raw=s))
            continue
        unparsed.append(i)
    return events, unparsed


def parse_file(path):
    with open(path, encoding="utf-8", errors="replace") as fh:
        return parse_lines(fh.readlines())
