from pcie_debug.parser import parse_lines
from pcie_debug.rules import check


def ids(text, **kw):
    ev, _ = parse_lines(text.strip().splitlines())
    return [v.rule_id for v in check(ev, **kw)]


def test_clean():
    assert ids("[10ns] TX MRd addr=0x0 len=4 tag=1\n[500ns] RX CplD tag=1 len=4 status=SC") == []

def test_orphan():
    assert ids("[10ns] RX CplD tag=5 len=1 status=SC") == ["R01"]

def test_dup_tag_and_lost():
    r = ids("[10ns] TX MRd addr=0x0 len=1 tag=1\n[20ns] TX MRd addr=0x4 len=1 tag=1")
    assert "R02" in r and "R07" in r

def test_len_mismatch():
    assert ids("[10ns] TX MRd addr=0x0 len=4 tag=1\n[50ns] RX CplD tag=1 len=2 status=SC") == ["R03"]

def test_timeout():
    assert ids("[10ns] TX MRd addr=0x0 len=1 tag=1\n[99999ns] RX CplD tag=1 len=1 status=SC") == ["R04"]

def test_ltssm_illegal():
    assert ids("[1ns] LTSSM Detect.Quiet -> L0") == ["R05"]

def test_ur_warning():
    assert ids("[10ns] TX MRd addr=0x0 len=1 tag=1\n[50ns] RX Cpl tag=1 len=1 status=UR") == ["R06"]

def test_bad_len():
    assert "R08" in ids("[10ns] TX MWr addr=0x0 len=0 tag=0")
