import tempfile, os
import pandas as pd
import streamlit as st
from pcie_debug.analyzer import analyze_file, summarize

st.set_page_config(page_title="PCIe Debug AI", layout="wide")
st.title("PCIe TLP Log Analyzer & AI Debug Assistant")
files = st.file_uploader("Upload simulation logs (.log)", type="log", accept_multiple_files=True)
use_llm = st.sidebar.checkbox("Use LLM explanations (needs ANTHROPIC_API_KEY)")
timeout = st.sidebar.number_input("Completion timeout (ns)", value=50_000, step=1000)

if files:
    runs = []
    for f in files:
        with tempfile.NamedTemporaryFile("wb", suffix=".log", delete=False) as tmp:
            tmp.write(f.getvalue())
        r = analyze_file(tmp.name, timeout); r["file"] = f.name; runs.append(r); os.unlink(tmp.name)
    s = summarize(runs, use_llm)
    c1, c2, c3 = st.columns(3)
    c1.metric("Tests", s["total"]); c2.metric("Passed", s["passed"]); c3.metric("Failed", s["failed"])
    st.subheader("Failures by rule")
    if s["by_rule"]:
        st.bar_chart(pd.Series({f"{k} {v['title']}": v["count"] for k, v in s["by_rule"].items()}))
        for rid, d in s["by_rule"].items():
            with st.expander(f"[{rid}] {d['title']} x{d['count']}"):
                st.write(f"**Root cause:** {d['root_cause']}")
                st.write(f"**Spec:** {d['spec_ref']}")
                st.write(f"**Suggested fix:** {d['suggested_fix']}")
                if d.get("llm_analysis"): st.info(d["llm_analysis"])
                st.code("\n".join(d["examples"]))
    st.subheader("All runs")
    st.dataframe(pd.DataFrame([{"file": r["file"], "status": r["status"], "violations": len(r["violations"])} for r in runs]))
else:
    st.info("Upload logs, or generate samples with: python scripts/gen_logs.py")
