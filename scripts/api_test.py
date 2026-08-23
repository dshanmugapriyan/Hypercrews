"""Quick API health-check for ScamCheck endpoints."""
import time
import requests

BASE = "http://localhost:8000/api"

def check(label, fn):
    try:
        result = fn()
        print(f"[OK]   {label}: {result}")
    except Exception as e:
        print(f"[FAIL] {label}: {e}")

# 1 — History
def history():
    r = requests.get(f"{BASE}/history", timeout=5)
    r.raise_for_status()
    return f"{len(r.json())} records"

check("/api/history", history)

# 2 — Registry
def registry():
    r = requests.get(f"{BASE}/settings/registry", timeout=5)
    r.raise_for_status()
    data = r.json()
    lines = []
    for k, v in data.items():
        m = v.get("metrics", {})
        p = round(m.get("precision", 0) * 100, 2) if m.get("precision") else None
        rec = round(m.get("recall", 0) * 100, 2) if m.get("recall") else None
        f1 = round(m.get("f1_score", 0) * 100, 2) if m.get("f1_score") else None
        auc = round(m.get("roc_auc", 0) * 100, 2) if m.get("roc_auc") else None
        lines.append(f"\n    {k}: Precision={p}% Recall={rec}% F1={f1}% ROC-AUC={auc}%")
    return "".join(lines)

check("/api/settings/registry", registry)

# 3 — Submit scan
def submit_scan():
    payload = {
        "input_type": "TEXT",
        "text": "Urgent: Pay 150 USD registration fee to secure your remote job slot. Send bank OTP and PAN card photo immediately via WhatsApp."
    }
    r = requests.post(f"{BASE}/scan", json=payload, timeout=10)
    r.raise_for_status()
    data = r.json()
    return "scan_id=" + data.get("id", "")[:12] + " status=" + str(data.get("status"))

check("/api/scan POST", submit_scan)

# 4 — Wait 6s then get latest scan report from history
def check_report():
    time.sleep(8)
    r = requests.get(f"{BASE}/history", timeout=5)
    r.raise_for_status()
    scans = r.json()
    if not scans:
        return "no scans in history"
    latest = scans[0]
    sid = latest["id"]
    r2 = requests.get(f"{BASE}/report/{sid}", timeout=10)
    if r2.status_code == 400:
        return f"scan {sid[:8]} not yet COMPLETE (status={latest.get('status')})"
    r2.raise_for_status()
    report = r2.json()
    hero = report.get("hero", {})
    is_demo = report.get("is_demo_data")
    return (
        f"verdict={hero.get('verdict')} risk={hero.get('risk_score')}% "
        f"trust={hero.get('trust_score')}% confidence={hero.get('confidence')}% "
        f"is_demo={is_demo} evidence_count={len(report.get('evidence', []))}"
    )

check("/api/report (latest)", check_report)

# 5 — Copilot grounded query
def copilot():
    r = requests.get(f"{BASE}/history", timeout=5)
    scans = r.json()
    if not scans:
        return "no scans to test copilot"
    sid = scans[0]["id"]
    r2 = requests.post(f"{BASE}/copilot", json={"scan_id": sid, "message": "Should I reply to this recruiter?"}, timeout=10)
    r2.raise_for_status()
    data = r2.json()
    reply = data.get("reply", "")[:120]
    grounded = data.get("grounded_in_evidence_ids", [])
    return f"reply_preview={reply!r} grounded_ids_count={len(grounded)}"

check("/api/copilot POST", copilot)

print("\n[DONE] API verification complete.")
