import streamlit as st
import pandas as pd
import requests
import json
import time

# --- DESIGN & STYLE ---
st.set_page_config(
    page_title="Sentinel Shield v1.0 | Security Intelligence",
    page_icon="🛡️",
    layout="wide"
)

# Enterprise Cyber-Security Aesthetic
st.markdown("""
<style>
    .stApp { background-color: #050505; color: #ededed; }
    .stHeader { background-color: #0c0e12; border-bottom: 1px solid #1e293b; }
    .main-title { font-size: 2.2rem; font-weight: 800; color: #10b981; margin-bottom: 1.5rem; text-shadow: 0 0 15px rgba(16, 185, 129, 0.2); }
    .stat-card { background-color: #0c0e12; padding: 1.2rem; border: 1px solid #1e293b; border-radius: 12px; margin-bottom: 1rem; box-shadow: 0 4px 10px rgba(0,0,0,0.3); }
    .stat-label { font-size: 0.8rem; font-weight: bold; color: #64748b; text-transform: uppercase; letter-spacing: 0.1rem; }
    .stat-value { font-size: 2.2rem; font-weight: 800; color: #ffffff; }
    .blocked-value { color: #f43f5e; }
    .hours-value { color: #8b5cf6; }
    .stTextInput input { background-color: #0c0e12; border: 1px solid #1e293b; border-radius: 8px; color: #ededed; height: 50px; font-size: 1rem; }
    .alert-log { background-color: #080a0d; font-family: 'Courier New', monospace; padding: 1rem; border-left: 4px solid #f43f5e; border-radius: 4px; font-size: 0.85rem; color: #fb7185; margin: 0.5rem 0; overflow-x: auto; }
</style>
""", unsafe_allow_html=True)

API_URL = "http://localhost:8000"

# --- DATA FETCHING ---
def get_status():
    try:
        res = requests.get(f"{API_URL}/status", timeout=2)
        return res.json()
    except Exception as e:
        return None

status = get_status()

# --- SIDEBAR & NAVIGATION ---
st.sidebar.markdown("<h2 style='color: #10b981;'>SENTINEL SHIELD</h2>", unsafe_allow_html=True)
st.sidebar.caption("v1.0.0 Production Build")
st.sidebar.success("AIR-GAPPED: Operational")
st.sidebar.markdown("---")

# Monthly Intelligence Summary
st.sidebar.write("### 📅 MONTHLY REPORT")
if status:
    stats = status.get("stats", {})
    st.sidebar.metric("BLOCKED LEAKS", stats.get("leaks_blocked", 0))
    st.sidebar.metric("HOURS SAVED (SEARCH)", stats.get("hours_saved", 0))
else:
    st.sidebar.info("Syncing stats...")

# --- MAIN DASHBOARD ---
st.markdown("<div class='main-title'>Guardian Intelligence Interface</div>", unsafe_allow_html=True)

col_a, col_b = st.columns([1, 1])

with col_a:
    st.markdown("<div class='stat-card'><div class='stat-label'>Vault Status</div><div class='stat-value'>SECURED</div></div>", unsafe_allow_html=True)
    
    st.subheader("🛡️ Security Audit Log")
    if status and status.get("alerts"):
        for alert in reversed(status['alerts'][:10]):
            st.markdown(f"<div class='alert-log'>{alert.strip()}</div>", unsafe_allow_html=True)
    else:
        st.write("No critical threats intercepted.")

with col_b:
    st.markdown("<div class='stat-card'><div class='stat-label'>Blocked Threats</div><div class='stat-value blocked-value'>" + str(status.get('stats', {}).get('leaks_blocked', 0) if status else 0) + "</div></div>", unsafe_allow_html=True)
    
    st.subheader("📊 Vulnerability Distribution")
    if status and status.get("files"):
        df = pd.DataFrame.from_dict(status['files'], orient='index')
        st.bar_chart(df['score'], color="#f43f5e")
    else:
        st.write("Awaiting initial file ingestion heatmap...")

st.markdown("---")

# --- SECURE QUERY TERMINAL ---
st.markdown("### 💬 Local Intelligence Query")
st.caption("Ask specific questions about clinical or legal records. All PII is surgically redacted.")

query = st.text_input("QUERY SECURE VAULT", placeholder="How much was the Smith settlement in 2018?")

if st.button("EXECUTE ANALYSIS"):
    if not query:
        st.error("Illegal Input: No query detected.")
    else:
        with st.spinner("Analyzing air-gapped data..."):
            try:
                res = requests.post(f"{API_URL}/ask", json={"prompt": query})
                payload = res.json()
                
                st.markdown("#### SENTINEL ANALYSIS")
                st.info(payload['answer'])
                
                with st.expander("TRACE & COMPLIANCE DATA"):
                    st.write(f"**Safety Scan:** {payload['findings_alert']}")
                    st.write("**Sources Traced:**")
                    for s in payload['sources']:
                        st.code(f"Source Trace: {s}")
            except Exception as e:
                st.error(f"Engine Offline: {e}")

# Production Sync
if st.button("System Heartbeat Sync"):
    st.rerun()
