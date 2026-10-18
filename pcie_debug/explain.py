"""Explain violations: offline knowledge base, optionally enhanced by an LLM."""
import os

KB = {
    "R01": ("Orphan completion",
            "The completer answered a request the requester never sent, or the tag was already retired (e.g. duplicate or late completion).",
            "PCIe Base Spec: Transaction Layer, Completion handling (tag matching)",
            "Check tag allocation/free logic in the requester and whether the completer replays or duplicates completions."),
    "R02": ("Duplicate tag in flight",
            "A new non-posted request reused a tag that still has an outstanding request, so completions become ambiguous.",
            "PCIe Base Spec: Tag field / outstanding request tracking",
            "Inspect the tag allocator: tags must be freed only when the final completion is received."),
    "R03": ("Completion length mismatch",
            "CplD payload length differs from the requested length; often a byte-count or Lower Address calculation bug.",
            "PCIe Base Spec: Completion rules, Byte Count / Length fields",
            "Check completer payload splitting and the Length/Byte Count computation."),
    "R04": ("Completion timeout",
            "A completion arrived later than the allowed window; the requester may already have declared a timeout.",
            "PCIe Base Spec: Completion Timeout mechanism",
            "Look for stalls in the completer pipeline, credit starvation, or a link entering Recovery mid-transaction."),
    "R05": ("Illegal LTSSM transition",
            "The link training state machine moved between states not allowed by the spec, or the log is missing a transition.",
            "PCIe Base Spec: Physical Layer, LTSSM",
            "Check the LTSSM state encoding, timeout counters, and the exit conditions of the prior state."),
    "R06": ("Error completion status (UR/CA)",
            "The target returned Unsupported Request or Completer Abort, usually an address-decode or config-space issue.",
            "PCIe Base Spec: Completion Status, Error Handling",
            "Verify the address map / BAR setup and that the request type is supported by the target."),
    "R07": ("Request never completed",
            "A non-posted request was still outstanding at end of simulation; likely a hang or a dropped completion.",
            "PCIe Base Spec: Non-posted request / completion pairing",
            "Check for dropped TLPs, flow control deadlock, or the test ending too early."),
    "R08": ("Invalid TLP length",
            "TLP length is zero or exceeds the maximum payload size (1024 DW).",
            "PCIe Base Spec: TLP header Length field",
            "Check the TLP header builder and length encoding (0 encodes 1024 DW on the wire)."),
}


def offline(rule_id):
    title, cause, spec, fix = KB.get(rule_id, ("Unknown", "No knowledge-base entry.", "-", "-"))
    return {"title": title, "root_cause": cause, "spec_ref": spec, "suggested_fix": fix}


def llm_explain(rule_id, examples):
    """Ask an LLM for a deeper explanation. Returns None if no key/SDK/network."""
    if not os.getenv("ANTHROPIC_API_KEY"):
        return None
    try:
        import anthropic
        client = anthropic.Anthropic()
        info = offline(rule_id)
        prompt = (
            "You are a PCIe verification expert helping an RTL engineer debug a regression failure.\n"
            f"Rule: {rule_id} - {info['title']}\nReference: {info['spec_ref']}\n"
            "Example violations from the log:\n" + "\n".join(f"- {e}" for e in examples[:5]) +
            "\n\nIn under 120 words give: the most likely root cause, and what to check in the RTL/testbench first."
        )
        msg = client.messages.create(model=os.getenv("PCIE_DEBUG_MODEL", "claude-sonnet-5-5"),
                                     max_tokens=400, messages=[{"role": "user", "content": prompt}])
        return "".join(b.text for b in msg.content if b.type == "text")
    except Exception:
        return None


def explain_rule(rule_id, examples, use_llm=True):
    out = offline(rule_id)
    if use_llm:
        out["llm_analysis"] = llm_explain(rule_id, examples)
    return out
