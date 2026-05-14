"""
DPAI v2.0 — Streamlit Frontend
Premium SaaS Invoice Automation Dashboard
"""
import json, time
import streamlit as st
import requests
import pandas as pd

API_BASE = "http://localhost:8000"
st.set_page_config(page_title="DPAI Invoice Automation", page_icon="📄", layout="wide", initial_sidebar_state="expanded")

# ── CSS ──────────────────────────────────────────────────────────────────────
st.markdown("""<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');
.stApp { font-family: 'Inter', sans-serif; }
.dpai-header { background: linear-gradient(135deg, #0f0c29 0%, #302b63 50%, #24243e 100%); padding: 2rem 2.5rem; border-radius: 16px; margin-bottom: 2rem; box-shadow: 0 8px 32px rgba(48,43,99,0.35); position: relative; overflow: hidden; }
.dpai-header h1 { color: #fff; font-size: 2rem; font-weight: 700; margin: 0; }
.dpai-header p { color: rgba(255,255,255,0.7); font-size: 1rem; margin: 0.5rem 0 0; font-weight: 300; }
.dpai-badge { display: inline-block; background: linear-gradient(135deg, #6366f1, #8b5cf6); color: white; padding: 4px 12px; border-radius: 20px; font-size: 0.75rem; font-weight: 600; margin-bottom: 0.5rem; letter-spacing: 1px; }
.result-card { background: linear-gradient(145deg, #1e1b4b, #1a1744); border: 1px solid rgba(99,102,241,0.2); border-radius: 14px; padding: 1.5rem; margin: 0.75rem 0; box-shadow: 0 4px 20px rgba(0,0,0,0.2); }
.result-card:hover { transform: translateY(-2px); box-shadow: 0 8px 30px rgba(99,102,241,0.15); }
.result-card h3 { color: #a5b4fc; font-size: 0.8rem; font-weight: 600; text-transform: uppercase; letter-spacing: 1.5px; margin: 0 0 0.5rem; }
.result-card .value { color: #fff; font-size: 1.25rem; font-weight: 600; }
.conf-bar { height: 4px; border-radius: 2px; margin-top: 8px; background: rgba(255,255,255,0.1); }
.conf-fill { height: 100%; border-radius: 2px; }
.conf-high { background: linear-gradient(90deg, #10b981, #34d399); }
.conf-med { background: linear-gradient(90deg, #f59e0b, #fbbf24); }
.conf-low { background: linear-gradient(90deg, #ef4444, #f87171); }
.status-valid { background: linear-gradient(135deg, #059669, #10b981); color: white; padding: 6px 16px; border-radius: 20px; font-size: 0.85rem; font-weight: 600; display: inline-block; }
.status-warning { background: linear-gradient(135deg, #d97706, #f59e0b); color: white; padding: 6px 16px; border-radius: 20px; font-size: 0.85rem; font-weight: 600; display: inline-block; }
.status-invalid { background: linear-gradient(135deg, #dc2626, #ef4444); color: white; padding: 6px 16px; border-radius: 20px; font-size: 0.85rem; font-weight: 600; display: inline-block; }
.issue-item { padding: 0.75rem 1rem; border-radius: 10px; margin: 0.5rem 0; font-size: 0.9rem; }
.issue-error { background: rgba(239,68,68,0.12); border-left: 3px solid #ef4444; color: #fca5a5; }
.issue-warning { background: rgba(245,158,11,0.12); border-left: 3px solid #f59e0b; color: #fcd34d; }
.ocr-text-box { background: #0f0e1a; border: 1px solid rgba(99,102,241,0.15); border-radius: 12px; padding: 1.25rem; font-family: 'Courier New', monospace; font-size: 0.85rem; color: #c4b5fd; max-height: 400px; overflow-y: auto; white-space: pre-wrap; line-height: 1.6; }
.sidebar-section { background: rgba(99,102,241,0.06); border: 1px solid rgba(99,102,241,0.12); border-radius: 12px; padding: 1rem; margin: 0.75rem 0; }
.sidebar-section h4 { color: #a5b4fc; font-size: 0.8rem; font-weight: 600; text-transform: uppercase; letter-spacing: 1px; margin: 0 0 0.5rem; }
.hist-row { background: rgba(99,102,241,0.05); border: 1px solid rgba(99,102,241,0.1); border-radius: 10px; padding: 0.75rem 1rem; margin: 0.4rem 0; display: flex; justify-content: space-between; align-items: center; }
.hist-name { color: #e2e8f0; font-weight: 500; font-size: 0.9rem; }
.hist-meta { color: rgba(255,255,255,0.4); font-size: 0.75rem; }
.section-divider { border: none; border-top: 1px solid rgba(99,102,241,0.15); margin: 2rem 0; }
.pipeline-step { display: inline-flex; align-items: center; gap: 6px; padding: 6px 14px; border-radius: 8px; font-size: 0.8rem; font-weight: 500; }
.step-done { background: rgba(16,185,129,0.15); color: #34d399; border: 1px solid rgba(16,185,129,0.3); }
.step-active { background: rgba(99,102,241,0.2); color: #818cf8; border: 1px solid rgba(99,102,241,0.4); animation: pulse 1.5s infinite; }
.step-pending { background: rgba(255,255,255,0.03); color: rgba(255,255,255,0.3); border: 1px solid rgba(255,255,255,0.08); }
@keyframes pulse { 0%,100% { opacity:1; } 50% { opacity:0.6; } }
#MainMenu {visibility: hidden;} footer {visibility: hidden;} header {visibility: hidden;}
</style>""", unsafe_allow_html=True)


def api_get(path, **kw):
    try:
        r = requests.get(f"{API_BASE}{path}", timeout=5, **kw)
        return r.json() if r.status_code == 200 else None
    except Exception:
        return None

def api_health():
    return api_get("/health")

def run_pipeline(file_bytes, filename):
    try:
        r = requests.post(f"{API_BASE}/pipeline", files={"file": (filename, file_bytes)}, timeout=120)
        return r.json() if r.status_code == 200 else None
    except requests.ConnectionError:
        st.error("Cannot connect to backend API. Start it with: python -m uvicorn backend.main:app --port 8000")
        return None
    except Exception as e:
        st.error(f"Error: {e}")
        return None

def update_field(doc_id, field, value):
    try:
        r = requests.post(f"{API_BASE}/update", params={"document_id": doc_id, "field": field, "value": value}, timeout=5)
        return r.json() if r.status_code == 200 else None
    except Exception:
        return None

def conf_bar_html(conf):
    pct = int(conf * 100)
    cls = "conf-high" if conf >= 0.8 else ("conf-med" if conf >= 0.5 else "conf-low")
    return f'<div class="conf-bar"><div class="conf-fill {cls}" style="width:{pct}%"></div></div><div style="color:rgba(255,255,255,0.35);font-size:0.7rem;margin-top:2px">{pct}% confidence</div>'

def badge(status):
    css = {"valid":"status-valid","warning":"status-warning","invalid":"status-invalid"}.get(status,"status-warning")
    icon = {"valid":"✅","warning":"⚠️","invalid":"❌"}.get(status,"❓")
    return f'<span class="{css}">{icon} {status.upper()}</span>'


# ═══════════════════════════════════════════════════════════════════════════
#  SESSION STATE
# ═══════════════════════════════════════════════════════════════════════════
if "history" not in st.session_state:
    st.session_state.history = []
if "active_result" not in st.session_state:
    st.session_state.active_result = None

# ═══════════════════════════════════════════════════════════════════════════
#  SIDEBAR
# ═══════════════════════════════════════════════════════════════════════════
with st.sidebar:
    st.markdown('<div style="text-align:center;padding:1rem 0"><div style="font-size:2.5rem">📄</div><div style="font-size:1.2rem;font-weight:700;color:#a5b4fc;letter-spacing:2px">DPAI</div><div style="font-size:0.7rem;color:rgba(255,255,255,0.35);margin-top:2px">v2.0 Production</div></div>', unsafe_allow_html=True)
    st.markdown("---")

    health = api_health()
    if health:
        ocr_engine = health.get("ocr_engine", "EasyOCR")
        doc_count = health.get("documents_processed", 0)
        st.markdown(f'<div class="sidebar-section"><h4>🟢 System Status</h4><div style="color:#10b981;font-weight:500">API Online</div></div>', unsafe_allow_html=True)
        st.markdown(f'<div class="sidebar-section"><h4>🔍 OCR Engine</h4><div style="color:#818cf8;font-weight:500">{ocr_engine} (Real OCR)</div></div>', unsafe_allow_html=True)
        st.markdown(f'<div class="sidebar-section"><h4>📊 Processed</h4><div style="color:#818cf8;font-size:1.5rem;font-weight:700">{doc_count}</div></div>', unsafe_allow_html=True)
    else:
        st.markdown('<div class="sidebar-section"><h4>🔴 System Status</h4><div style="color:#ef4444;font-weight:500">API Offline</div><div style="color:rgba(255,255,255,0.4);font-size:0.75rem;margin-top:4px">Run: python -m uvicorn backend.main:app</div></div>', unsafe_allow_html=True)

    st.markdown("---")
    st.markdown('<div style="color:#a5b4fc;font-size:0.8rem;font-weight:600;text-transform:uppercase;letter-spacing:1px;margin-bottom:0.5rem">📥 Export All</div>', unsafe_allow_html=True)

    ec1, ec2, ec3 = st.columns(3)
    with ec1:
        if st.button("CSV", use_container_width=True, key="sb_csv"):
            d = api_get("/export/csv")
            if d: st.download_button("⬇", data=str(d), file_name="invoices.csv", mime="text/csv", key="dl_c")
            else: st.warning("No data")
    with ec2:
        if st.button("JSON", use_container_width=True, key="sb_json"):
            d = api_get("/export/json")
            if d: st.download_button("⬇", data=json.dumps(d,indent=2), file_name="invoices.json", mime="application/json", key="dl_j")
            else: st.warning("No data")
    with ec3:
        if st.button("Excel", use_container_width=True, key="sb_xlsx"):
            try:
                r = requests.get(f"{API_BASE}/export/excel", timeout=10)
                if r.status_code == 200:
                    st.download_button("⬇", data=r.content, file_name="invoices.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", key="dl_x")
                else: st.warning("No data")
            except Exception: st.warning("Export failed")

    # History in sidebar
    if st.session_state.history:
        st.markdown("---")
        st.markdown('<div style="color:#a5b4fc;font-size:0.8rem;font-weight:600;text-transform:uppercase;letter-spacing:1px;margin-bottom:0.5rem">📁 History</div>', unsafe_allow_html=True)
        for i, h in enumerate(reversed(st.session_state.history[-10:])):
            vs = h.get("validation",{}).get("status","")
            ic = {"valid":"🟢","warning":"🟡","invalid":"🔴"}.get(vs,"⏳")
            fname = h.get("filename","")[:22]
            if st.button(f"{ic} {fname}", key=f"hist_{i}", use_container_width=True):
                st.session_state.active_result = h


# ═══════════════════════════════════════════════════════════════════════════
#  MAIN
# ═══════════════════════════════════════════════════════════════════════════
st.markdown("""<div class="dpai-header"><div class="dpai-badge">REAL OCR • PRODUCTION</div><h1>Document & Process Automation</h1><p>Upload invoices → Real OCR extraction → Validate → Export. Powered by EasyOCR engine.</p></div>""", unsafe_allow_html=True)

# ── Tabs ─────────────────────────────────────────────────────────────────
tab_upload, tab_history = st.tabs(["📤 Upload & Process", "📋 Invoice History"])

with tab_upload:
    uploaded_files = st.file_uploader(
        "Drop invoice files here (multi-file supported)",
        type=["pdf","png","jpg","jpeg","tiff","bmp","webp"],
        accept_multiple_files=True,
        help="Supported: PDF, PNG, JPG, JPEG, TIFF, BMP, WEBP (max 20 MB each)",
    )

    if uploaded_files:
        for uf in uploaded_files:
            c1,c2,c3 = st.columns([3,1,1])
            c1.text(f"📎 {uf.name}")
            c2.text(f"{len(uf.getvalue())/1024:.0f} KB")
            c3.text(uf.name.rsplit('.',1)[-1].upper())

        st.markdown('<hr class="section-divider">', unsafe_allow_html=True)

        if st.button("🚀 Process All Invoices", type="primary", use_container_width=True):
            progress = st.progress(0, text="Starting pipeline...")
            status_area = st.empty()
            results_collector = []

            for idx, uf in enumerate(uploaded_files):
                file_bytes = uf.getvalue()
                pct = int((idx / len(uploaded_files)) * 100)
                progress.progress(pct, text=f"Processing {uf.name}...")

                # Pipeline steps display
                status_area.markdown(f"""<div style="display:flex;gap:8px;flex-wrap:wrap;margin:1rem 0">
                    <div class="pipeline-step step-done">✓ Upload</div>
                    <div class="pipeline-step step-active">⟳ OCR</div>
                    <div class="pipeline-step step-pending">Extract</div>
                    <div class="pipeline-step step-pending">Validate</div>
                </div><div style="color:rgba(255,255,255,0.5);font-size:0.85rem">Processing: {uf.name}</div>""", unsafe_allow_html=True)

                result = run_pipeline(file_bytes, uf.name)

                if result:
                    results_collector.append(result)
                    st.session_state.history.append(result)

            progress.progress(100, text="Complete!")
            status_area.markdown(f"""<div style="display:flex;gap:8px;flex-wrap:wrap;margin:1rem 0">
                <div class="pipeline-step step-done">✓ Upload</div>
                <div class="pipeline-step step-done">✓ OCR</div>
                <div class="pipeline-step step-done">✓ Extract</div>
                <div class="pipeline-step step-done">✓ Validate</div>
            </div>""", unsafe_allow_html=True)

            if results_collector:
                st.session_state.active_result = results_collector[-1]
                st.success(f"✅ {len(results_collector)} invoice(s) processed successfully!")
                time.sleep(0.5)
                st.rerun()

    # ── Display Active Result ────────────────────────────────────────────
    if st.session_state.active_result:
        result = st.session_state.active_result
        extracted = result.get("extracted_data", {})
        validation = result.get("validation", {})
        confidences = extracted.get("confidence", {})
        proc_time = result.get("processing_time_ms")

        st.markdown('<hr class="section-divider">', unsafe_allow_html=True)

        # Status bar
        v_status = validation.get("status", "unknown")
        fields_found = validation.get("fields_found", 0)
        fields_total = validation.get("fields_total", 4)
        overall_conf = extracted.get("overall_confidence", 0)
        time_str = f" • {proc_time}ms" if proc_time else ""

        st.markdown(f"""<div style="display:flex;align-items:center;justify-content:space-between;margin:1rem 0;flex-wrap:wrap;gap:8px">
            <div>{badge(v_status)} <span style="color:rgba(255,255,255,0.5);margin-left:12px;font-size:0.85rem">{fields_found}/{fields_total} fields • {int(overall_conf*100)}% confidence{time_str}</span></div>
            <div style="color:rgba(255,255,255,0.4);font-size:0.85rem">📄 {result.get('filename','')}</div>
        </div>""", unsafe_allow_html=True)

        # ── Document Type Detection Warning ──────────────────────────
        is_invoice = extracted.get("is_invoice", True)
        detection_msg = extracted.get("detection_message", "")
        raw_text_len = extracted.get("raw_text_length", 0)

        if not is_invoice:
            st.error(f"⚠️ **Not an Invoice**: {detection_msg}")
            st.info(f"📝 The OCR extracted {raw_text_len} characters of text, but no invoice fields were found. This file may not be an invoice document.")
        elif fields_found == 0 and raw_text_len > 0:
            st.warning(f"⚠️ OCR extracted {raw_text_len} characters but no invoice fields were recognized. The document format may be unusual.")
        elif fields_found == 0 and raw_text_len == 0:
            st.error("❌ OCR could not extract any text from this file. The image may be too blurry, too small, or in an unsupported format.")

        # ── OCR Text Preview (always visible when fields are missing) ─
        if fields_found < fields_total:
            preview = extracted.get("raw_text_preview", "")
            if preview:
                st.markdown("### 🔍 OCR Text Preview")
                st.markdown(f'<div class="ocr-text-box">{preview}</div>', unsafe_allow_html=True)
                st.caption(f"Showing first 500 chars of {raw_text_len} total characters extracted")

        # ── Extracted Data Cards ─────────────────────────────────────
        st.markdown("### 📋 Extracted Data")
        c1, c2 = st.columns(2)

        def card(label, icon, value, conf_key):
            v = value or "—"
            c = confidences.get(conf_key, 0)
            return f'<div class="result-card"><h3>{icon} {label}</h3><div class="value">{v}</div>{conf_bar_html(c)}</div>'

        with c1:
            st.markdown(card("Invoice Number", "🔖", extracted.get("invoice_number"), "invoice_number"), unsafe_allow_html=True)
            st.markdown(card("Vendor Name", "🏢", extracted.get("vendor_name"), "vendor_name"), unsafe_allow_html=True)
        with c2:
            st.markdown(card("Invoice Date", "📅", extracted.get("date"), "date"), unsafe_allow_html=True)
            amt = extracted.get("total_amount")
            amt_display = f"₹{amt}" if amt else "—"
            c_amt = confidences.get("total_amount", 0)
            st.markdown(f'<div class="result-card"><h3>💰 Total Amount</h3><div class="value">{amt_display}</div>{conf_bar_html(c_amt)}</div>', unsafe_allow_html=True)

        # GST
        gst = extracted.get("gst")
        if gst:
            st.markdown("### 🏛️ GST Details")
            cols = st.columns(max(len(gst), 1))
            for i, (k, v) in enumerate(gst.items()):
                with cols[i % len(cols)]:
                    st.markdown(f'<div class="result-card"><h3>{k.upper().replace("_"," ")}</h3><div class="value" style="font-size:1.1rem">{v}</div></div>', unsafe_allow_html=True)

        # ── Edit Fields ──────────────────────────────────────────────
        with st.expander("✏️ Edit Extracted Fields", expanded=False):
            doc_id = result.get("document_id", "")
            ec1, ec2 = st.columns(2)
            with ec1:
                new_inv = st.text_input("Invoice Number", value=extracted.get("invoice_number") or "", key="edit_inv")
                new_vendor = st.text_input("Vendor Name", value=extracted.get("vendor_name") or "", key="edit_vendor")
            with ec2:
                new_date = st.text_input("Date", value=extracted.get("date") or "", key="edit_date")
                new_amount = st.text_input("Total Amount", value=extracted.get("total_amount") or "", key="edit_amount")

            if st.button("💾 Save Changes", key="save_edits"):
                updates = {"invoice_number": new_inv, "date": new_date, "vendor_name": new_vendor, "total_amount": new_amount}
                for field, val in updates.items():
                    if val != (extracted.get(field) or ""):
                        update_field(doc_id, field, val)
                st.success("Fields updated!")
                st.rerun()

        # ── Validation Issues ────────────────────────────────────────
        errors = validation.get("errors", [])
        warnings = validation.get("warnings", [])
        if errors or warnings:
            st.markdown("### ⚡ Validation Report")
            for err in errors:
                st.markdown(f'<div class="issue-item issue-error"><strong>❌ {err["field"].upper()}</strong>: {err["message"]}</div>', unsafe_allow_html=True)
            for w in warnings:
                st.markdown(f'<div class="issue-item issue-warning"><strong>⚠️ {w["field"].upper()}</strong>: {w["message"]}</div>', unsafe_allow_html=True)

        if validation.get("is_duplicate"):
            st.warning(f"🔄 Possible duplicate of document: `{validation.get('duplicate_of')}`")

        # ── Raw OCR Text (full, expandable) ──────────────────────────
        with st.expander("🔍 Full Raw OCR Text", expanded=False):
            raw_text = result.get("raw_text", "")
            if raw_text:
                st.markdown(f'<div class="ocr-text-box">{raw_text}</div>', unsafe_allow_html=True)
                st.caption(f"Total: {len(raw_text)} characters")
            else:
                st.warning("No text was extracted from this document.")

        # ── Export single ────────────────────────────────────────────
        st.markdown('<hr class="section-divider">', unsafe_allow_html=True)
        st.markdown("### 📥 Export This Invoice")
        ex1, ex2 = st.columns(2)
        with ex1:
            st.download_button("📊 CSV", data=json.dumps(extracted, indent=2, default=str), file_name=f"invoice_{result.get('document_id','')}.json", mime="application/json", use_container_width=True, key="exp_csv_single")
        with ex2:
            st.download_button("📋 JSON", data=json.dumps(result, indent=2, default=str), file_name=f"invoice_{result.get('document_id','')}_full.json", mime="application/json", use_container_width=True, key="exp_json_single")

    elif not uploaded_files:
        st.markdown("""<div style="text-align:center;padding:3rem 2rem;margin:2rem 0">
            <div style="font-size:4rem;margin-bottom:1rem">📄</div>
            <h3 style="color:#a5b4fc;font-weight:600">Upload invoices to get started</h3>
            <p style="color:rgba(255,255,255,0.4);max-width:500px;margin:0.5rem auto">Drop PDF or image files above. Real OCR will extract text from your actual documents — no demo data.</p>
            <div style="margin-top:2rem;display:flex;justify-content:center;gap:2rem">
                <div style="text-align:center"><div style="font-size:1.5rem">🔍</div><div style="color:rgba(255,255,255,0.5);font-size:0.85rem;margin-top:4px">OCR Scan</div></div>
                <div style="text-align:center"><div style="font-size:1.5rem">📊</div><div style="color:rgba(255,255,255,0.5);font-size:0.85rem;margin-top:4px">Extract</div></div>
                <div style="text-align:center"><div style="font-size:1.5rem">✅</div><div style="color:rgba(255,255,255,0.5);font-size:0.85rem;margin-top:4px">Validate</div></div>
                <div style="text-align:center"><div style="font-size:1.5rem">📥</div><div style="color:rgba(255,255,255,0.5);font-size:0.85rem;margin-top:4px">Export</div></div>
            </div>
        </div>""", unsafe_allow_html=True)


with tab_history:
    st.markdown("### 📋 Invoice History")

    # Search & filter
    fc1, fc2 = st.columns([3, 1])
    with fc1:
        search_q = st.text_input("🔍 Search by filename or vendor", key="hist_search", placeholder="Type to search...")
    with fc2:
        status_filter = st.selectbox("Status", ["All", "valid", "warning", "invalid"], key="hist_filter")

    history = st.session_state.history
    if search_q:
        sq = search_q.lower()
        history = [h for h in history if sq in h.get("filename","").lower() or sq in (h.get("extracted_data",{}).get("vendor_name","") or "").lower()]
    if status_filter != "All":
        history = [h for h in history if h.get("validation",{}).get("status") == status_filter]

    if history:
        st.markdown(f"**{len(history)} invoice(s)**")
        for i, h in enumerate(reversed(history)):
            ext = h.get("extracted_data", {})
            val = h.get("validation", {})
            vs = val.get("status", "")
            ic = {"valid":"🟢","warning":"🟡","invalid":"🔴"}.get(vs,"⏳")
            inv = ext.get("invoice_number") or "N/A"
            vendor = ext.get("vendor_name") or "Unknown"
            amount = ext.get("total_amount") or "—"
            conf = ext.get("overall_confidence", 0)

            st.markdown(f"""<div class="hist-row">
                <div><span class="hist-name">{ic} {h.get('filename','')[:30]}</span><br><span class="hist-meta">{inv} • {vendor[:25]} • ₹{amount}</span></div>
                <div style="text-align:right"><span style="color:#818cf8;font-weight:600">{int(conf*100)}%</span><br><span class="hist-meta">confidence</span></div>
            </div>""", unsafe_allow_html=True)

            if st.button(f"View Details", key=f"view_{i}", use_container_width=True):
                st.session_state.active_result = h
                st.rerun()
    else:
        st.info("No invoices processed yet. Upload files in the Upload tab.")


# Footer
st.markdown("""<div style="text-align:center;padding:2rem 0;margin-top:3rem;border-top:1px solid rgba(99,102,241,0.1)">
    <span style="color:rgba(255,255,255,0.3);font-size:0.8rem">DPAI v2.0 — Document & Process Automation Intelligence • Real OCR Engine</span>
</div>""", unsafe_allow_html=True)
