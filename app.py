import base64
import csv
import io
import json
import os
import random
import re
import smtplib
import socket
import socketserver
import sqlite3
import sys
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
from email.message import EmailMessage
from http.server import BaseHTTPRequestHandler, HTTPServer
import webbrowser

from openpyxl import load_workbook

# Base directories
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
WEB_DIR = os.path.join(BASE_DIR, "web")

# Serverless & Read-Only Filesystem Safe Storage
def get_writable_dir():
    if os.environ.get("VERCEL") or os.environ.get("AWS_LAMBDA_FUNCTION_NAME"):
        return "/tmp"
    try:
        test_path = os.path.join(BASE_DIR, ".write_test")
        with open(test_path, "w") as f:
            f.write("1")
        os.remove(test_path)
        return BASE_DIR
    except Exception:
        return "/tmp"

DATA_DIR = get_writable_dir()
DB_PATH = os.path.join(DATA_DIR, "campaigns.db")
LOG_PATH = os.path.join(DATA_DIR, "sent_log.txt")
CONFIG_PATH = os.path.join(DATA_DIR, "config.json")

# If running on serverless (/tmp), clone initial DB & config from project root if present
if DATA_DIR != BASE_DIR:
    import shutil
    base_db = os.path.join(BASE_DIR, "campaigns.db")
    if os.path.exists(base_db) and not os.path.exists(DB_PATH):
        try:
            shutil.copy2(base_db, DB_PATH)
        except Exception:
            pass
    base_cfg = os.path.join(BASE_DIR, "config.json")
    if os.path.exists(base_cfg) and not os.path.exists(CONFIG_PATH):
        try:
            shutil.copy2(base_cfg, CONFIG_PATH)
        except Exception:
            pass

# ============================================================
# DRY RUN TOGGLE
# If True : DRY RUN mode (simulates everything, no real emails sent)
# If False: FINAL MAILING mode (sends real emails via SMTP)
# ============================================================
DRY_RUN = False

# Default configurations
DEFAULT_CONFIG = {
    "dry_run": DRY_RUN,
    "sender_email": os.environ.get("SENDER_EMAIL", ""),
    "app_password": os.environ.get("GMAIL_APP_PASSWORD", "").replace(" ", "").strip(),
    "sender_name": os.environ.get("SENDER_NAME", ""),
    "smtp_server": "smtp.gmail.com",
    "smtp_port": 465,
    "buffer_delay_min": 3.0,
    "buffer_delay_max": 4.5,
    "max_per_run": 50,
}


def load_config():
    if os.path.exists(CONFIG_PATH):
        try:
            with open(CONFIG_PATH, "r", encoding="utf-8") as f:
                return {**DEFAULT_CONFIG, **json.load(f)}
        except Exception:
            pass
    return DEFAULT_CONFIG.copy()


def save_config(cfg):
    try:
        # Sanitize app password: remove spaces and strip
        if "app_password" in cfg:
            cfg["app_password"] = str(cfg["app_password"]).replace(" ", "").strip()
        if "sender_email" in cfg:
            cfg["sender_email"] = str(cfg["sender_email"]).strip()
        if "sender_name" in cfg:
            cfg["sender_name"] = str(cfg["sender_name"]).strip()

        with open(CONFIG_PATH, "w", encoding="utf-8") as f:
            json.dump(cfg, f, indent=2)
    except Exception as e:
        print(f"Error saving config: {e}")


DEFAULT_TEMPLATES = [
    (
        "🤝 Thank You & Networking",
        "",
        """Hi {{name}},

Thank you so much for taking the time to connect with me. I truly appreciate your support, encouragement, and guidance.

I am Rakshit Singh, a Computer Science undergraduate at JECRC University, Jaipur, with a strong focus on backend systems, full-stack applications, and AI/ML. Connecting with experienced professionals and alumni like you in the Delhi NCR tech and business community is a great source of learning and motivation for me.

I would love to stay in touch for any advice, mentorship, or future collaborations.

GitHub: https://github.com/rakshitsinghhh
Portfolio: https://rakshitsingh.online
LinkedIn: https://linkedin.com/in/rakshit-singh-5b7533248

Thank you once again for your kindness and time.

Warm regards,
Rakshit Singh
+91-9024534907"""
    ),
    (
        "💼 Job Application / SDE",
        "Application for Software Engineering Opportunities – Rakshit Singh",
        """Hi {{name}},

I'm Rakshit Singh, a Computer Science undergraduate at JECRC University, Jaipur, with hands-on experience building production-grade software across backend systems, full-stack applications, cloud infrastructure, and AI/ML.

Key highlights of my background:
• Built a compiler and virtual machine from scratch in C++.
• Developed a .NET 8 HRMS backend using Clean Architecture and CQRS.
• Created an AI chess engine analyzer using PyTorch and AlphaZero.
• Contributed to Microsoft's MCP Gateway (diagnosed and fixed a Content-Length proxy bug with regression tests).
• Team Lead at Smart India Hackathon 2025 (Top 10 finish among 150+ teams).

I am reaching out to explore potential Software Engineer or Intern roles at {{company}}. I've attached my resume for your consideration and would welcome the opportunity to discuss how I can contribute.

GitHub: https://github.com/rakshitsinghhh
Portfolio: https://rakshitsingh.online
LinkedIn: https://linkedin.com/in/rakshit-singh-5b7533248

Looking forward to connecting with you.

Best regards,
Rakshit Singh
+91-9024534907"""
    ),
    (
        "🔁 Quick Follow-Up",
        "Following up – Rakshit Singh",
        """Hi {{name}},

I hope you're having a productive week.

I wanted to quickly follow up on my previous note regarding software engineering opportunities. I know you must have a busy schedule, so I wanted to re-surface this in case it slipped past your inbox.

Please let me know if you would like me to share any additional details or work samples.

Thank you again for your time!

Best regards,
Rakshit Singh
+91-9024534907"""
    ),
    (
        "☕ 15-Min Coffee Chat",
        "Quick question / 15-min chat – Rakshit Singh",
        """Hi {{name}},

I hope you are doing well. I've been following your work and trajectory in the industry, and I truly admire your contributions.

As a final-year Computer Science student passionate about backend systems and distributed infrastructure, I would be deeply grateful for 15 minutes of your time for a quick virtual coffee chat. I'd love to ask a couple of quick questions about your career journey and learn from your perspective.

No worries at all if your calendar is full, but either way, thank you for being an inspiring leader in tech!

Warm regards,
Rakshit Singh
+91-9024534907"""
    )
]

# Initialize SQLite Database
def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("""
    CREATE TABLE IF NOT EXISTS campaigns (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        source_type TEXT,
        source_name TEXT,
        subject TEXT,
        body_template TEXT,
        attachment_name TEXT,
        total_recipients INTEGER DEFAULT 0,
        sent_count INTEGER DEFAULT 0,
        status TEXT DEFAULT 'pending'
    )
    """)
    c.execute("""
    CREATE TABLE IF NOT EXISTS campaign_recipients (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        campaign_id INTEGER,
        email TEXT,
        name TEXT,
        data_json TEXT,
        status TEXT DEFAULT 'pending',
        sent_at TIMESTAMP,
        error_message TEXT,
        FOREIGN KEY(campaign_id) REFERENCES campaigns(id)
    )
    """)
    c.execute("""
    CREATE TABLE IF NOT EXISTS templates (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT,
        subject TEXT,
        body TEXT,
        is_default INTEGER DEFAULT 0,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)
    # Seed default templates if table is empty
    count = c.execute("SELECT COUNT(*) FROM templates").fetchone()[0]
    if count == 0:
        c.executemany("INSERT INTO templates (name, subject, body, is_default) VALUES (?, ?, ?, 1)", DEFAULT_TEMPLATES)

    conn.commit()
    conn.close()


init_db()

# Global Sending State Manager
class CampaignManager:
    def __init__(self):
        self.lock = threading.RLock()
        self.active_thread = None
        self.stop_requested = False
        self.status = {
            "state": "idle",  # idle, sending, paused, completed, error
            "campaign_id": None,
            "campaign_title": "",
            "total": 0,
            "sent": 0,
            "failed": 0,
            "current_index": 0,
            "current_recipient": "",
            "current_status": "",
            "logs": [],
        }

    def reset_status(self, campaign_id, title, total):
        with self.lock:
            self.stop_requested = False
            self.status = {
                "state": "sending",
                "campaign_id": campaign_id,
                "campaign_title": title,
                "total": total,
                "sent": 0,
                "failed": 0,
                "current_index": 0,
                "current_recipient": "",
                "current_status": "Starting campaign...",
                "logs": [f"🚀 Campaign '{title}' started with {total} recipients."],
            }

    def add_log(self, msg):
        with self.lock:
            timestamp = time.strftime("%H:%M:%S")
            log_line = f"[{timestamp}] {msg}"
            self.status["logs"].append(log_line)
            if len(self.status["logs"]) > 200:
                self.status["logs"].pop(0)

    def update_progress(self, sent, failed, index, recipient, status_msg):
        with self.lock:
            self.status["sent"] = sent
            self.status["failed"] = failed
            self.status["current_index"] = index
            self.status["current_recipient"] = recipient
            self.status["current_status"] = status_msg

    def finish(self, final_state, msg):
        with self.lock:
            self.status["state"] = final_state
            self.status["current_status"] = msg
            self.add_log(msg)

    def request_stop(self):
        with self.lock:
            self.stop_requested = True
            self.status["current_status"] = "Stopping campaign..."
            self.add_log("⚠️ Stop requested by user.")

manager = CampaignManager()


# Helper: Extract clean email & variables
def sanitize_key(s):
    return re.sub(r"[^a-zA-Z0-9_]", "_", str(s).strip().lower()).strip("_")


def parse_csv_content(content_str):
    """Parse CSV text into columns and rows."""
    reader = csv.reader(io.StringIO(content_str))
    rows = [r for r in reader if any(field.strip() for field in r)]
    if not rows:
        return [], []

    raw_headers = [h.strip() for h in rows[0]]
    # Build clean attribute keys
    clean_keys = []
    seen = {}
    for h in raw_headers:
        base = sanitize_key(h) or "col"
        if base in seen:
            seen[base] += 1
            clean_keys.append(f"{base}_{seen[base]}")
        else:
            seen[base] = 0
            clean_keys.append(base)

    records = []
    for r in rows[1:]:
        rec = {}
        for idx, key in enumerate(clean_keys):
            val = r[idx].strip() if idx < len(r) else ""
            rec[key] = val
        records.append(rec)

    return raw_headers, clean_keys, records


def parse_excel_file(file_bytes):
    """Parse an Excel (.xlsx) file buffer."""
    wb = load_workbook(io.BytesIO(file_bytes), data_only=True)
    ws = wb.worksheets[0]
    raw_rows = list(ws.iter_rows(values_only=True))
    if not raw_rows:
        return [], [], []

    raw_headers = [str(c).strip() if c is not None else f"Col_{i+1}" for i, c in enumerate(raw_rows[0])]
    clean_keys = []
    seen = {}
    for h in raw_headers:
        base = sanitize_key(h) or "col"
        if base in seen:
            seen[base] += 1
            clean_keys.append(f"{base}_{seen[base]}")
        else:
            seen[base] = 0
            clean_keys.append(base)

    records = []
    for row in raw_rows[1:]:
        if not any(row):
            continue
        rec = {}
        for idx, key in enumerate(clean_keys):
            val = str(row[idx]).strip() if idx < len(row) and row[idx] is not None else ""
            rec[key] = val
        records.append(rec)

    return raw_headers, clean_keys, records


def fetch_google_sheet(sheet_url):
    """Fetch public Google Sheet as CSV."""
    m = re.search(r"/spreadsheets/d/([a-zA-Z0-9-_]+)", sheet_url)
    if not m:
        raise ValueError("Invalid Google Sheets URL. Could not find Sheet ID.")
    sheet_id = m.group(1)

    gid_match = re.search(r"[#&?]gid=([0-9]+)", sheet_url)
    gid = gid_match.group(1) if gid_match else "0"

    export_url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=csv&gid={gid}"
    req = urllib.request.Request(
        export_url,
        headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0 Safari/537.36"}
    )
    with urllib.request.urlopen(req, timeout=12) as response:
        content = response.read().decode("utf-8", errors="replace")
    return parse_csv_content(content)


def identify_fields(clean_keys, records):
    """Auto-detect email, name, and full name fields."""
    email_key = None
    name_key = None
    fullname_key = None

    # Check headers
    for k in clean_keys:
        if not email_key and ("email" in k or "mail" in k):
            email_key = k
        if not name_key and k in ("name", "first_name", "firstname"):
            name_key = k
        if not fullname_key and ("pura" in k or "full" in k):
            fullname_key = k

    # Fallback to inspecting content
    if not email_key and records:
        for k in clean_keys:
            if any("@" in str(r.get(k, "")) for r in records[:5]):
                email_key = k
                break

    if not name_key and clean_keys:
        for k in clean_keys:
            if k != email_key and ("name" in k):
                name_key = k
                break

    return {
        "email_field": email_key,
        "name_field": name_key,
        "fullname_field": fullname_key
    }


def render_template(template_str, contact):
    """Render {{placeholder}} in template with contact dict."""
    if not template_str:
        return ""

    def replace_match(match):
        key = sanitize_key(match.group(1))
        # Look for exact key or case-insensitive match
        for ck, val in contact.items():
            if sanitize_key(ck) == key:
                return str(val).strip()
        # Fallback for common aliases
        if key in ("name", "first_name") and "pura_name" in contact:
            return contact["pura_name"].split()[0]
        return ""

    rendered = re.sub(r"\{\{\s*([a-zA-Z0-9_]+)\s*\}\}", replace_match, template_str)
    # Also support single braces if any
    return rendered


def send_campaign_worker(campaign_id, config, subject_tpl, body_tpl, recipients, attachment=None, dry_run=False):
    """Background worker that dispatches campaign emails with buffer delay."""
    min_delay = float(config.get("buffer_delay_min", 3.0))
    max_delay = float(config.get("buffer_delay_max", 4.5))
    smtp_server = config.get("smtp_server", "smtp.gmail.com")
    smtp_port = int(config.get("smtp_port", 465))
    sender_email = str(config.get("sender_email", "")).strip()
    app_password = str(config.get("app_password", "")).replace(" ", "").strip()
    sender_name = str(config.get("sender_name", "")).strip() or sender_email.split("@")[0]

    sent_count = 0
    failed_count = 0
    total = len(recipients)

    if not dry_run and (not sender_email or not app_password):
        manager.finish("error", "Gmail sender email or 16-character App Password not set. Please connect your Gmail account in the top bar before sending.")
        return

    manager.add_log(f"Configured buffer delay: {min_delay:.1f}s - {max_delay:.1f}s between emails.")
    if dry_run:
        manager.add_log("🧪 Running in DRY RUN mode. (No real emails will be sent)")
    else:
        manager.add_log("🚀 Running in FINAL MAILING mode. (Real emails are being dispatched via Gmail SMTP)")

    smtp = None
    if not dry_run:
        try:
            manager.add_log(f"Connecting to Gmail SMTP ({smtp_server}:{smtp_port})...")
            smtp = smtplib.SMTP_SSL(smtp_server, smtp_port, timeout=20)
            smtp.login(sender_email, app_password)
            manager.add_log("✅ SMTP authenticated successfully.")
        except Exception as e:
            manager.finish("error", f"SMTP Connection Failed: {e}")
            return

    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    for idx, r in enumerate(recipients, start=1):
        if manager.stop_requested:
            manager.finish("stopped", f"Campaign stopped by user after {sent_count} sent.")
            break

        if r.get("skipped") or r.get("status") == "skipped":
            manager.add_log(f"⏭️ Skipping {r.get('email', 'contact')} (excluded during review)")
            continue

        email = r.get("email", "").strip()
        name = r.get("name", "").strip() or email

        if not email or "@" not in email:
            manager.add_log(f"⚠️ Skipping row {idx}: Invalid email ({email})")
            continue

        subj = r.get("subject") if r.get("subject") is not None else render_template(subject_tpl, r)
        body = r.get("body") if r.get("body") is not None else render_template(body_tpl, r)

        manager.update_progress(sent_count, failed_count, idx, email, f"Sending to {email}...")
        manager.add_log(f"[{idx}/{total}] Preparing email for {name} <{email}>")

        success = False
        err_msg = ""

        if dry_run:
            time.sleep(1.0)
            success = True
            sent_count += 1
            manager.add_log(f"✅ [Dry Run] Simulated send to {email}")
        else:
            try:
                msg = EmailMessage()
                msg["From"] = f"{sender_name} <{sender_email}>" if sender_name else sender_email
                msg["To"] = email
                if subj:
                    msg["Subject"] = subj
                msg.set_content(body)

                if attachment and attachment.get("bytes"):
                    msg.add_attachment(
                        attachment["bytes"],
                        maintype="application",
                        subtype=attachment.get("subtype", "octet-stream"),
                        filename=attachment.get("filename", "attachment")
                    )

                smtp.send_message(msg)
                success = True
                sent_count += 1
                manager.add_log(f"✅ Sent successfully to {email}")

                # Log to sent_log.txt
                try:
                    with open(LOG_PATH, "a", encoding="utf-8") as lf:
                        lf.write(email + "\n")
                except Exception:
                    pass

            except smtplib.SMTPServerDisconnected:
                manager.add_log("⚠️ SMTP dropped. Reconnecting...")
                try:
                    smtp = smtplib.SMTP_SSL(smtp_server, smtp_port, timeout=20)
                    smtp.login(sender_email, app_password)
                    smtp.send_message(msg)
                    success = True
                    sent_count += 1
                    manager.add_log(f"✅ Sent after reconnect to {email}")
                except Exception as ex2:
                    err_msg = str(ex2)
                    failed_count += 1
                    manager.add_log(f"❌ Failed to send to {email}: {ex2}")
            except Exception as e:
                err_msg = str(e)
                failed_count += 1
                manager.add_log(f"❌ Failed to send to {email}: {e}")

        # Record in DB
        c.execute("""
        INSERT INTO campaign_recipients (campaign_id, email, name, data_json, status, sent_at, error_message)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            campaign_id,
            email,
            name,
            json.dumps(r),
            "sent" if success else "failed",
            time.strftime("%Y-%m-%d %H:%M:%S") if success else None,
            err_msg
        ))
        conn.commit()

        # Update Progress
        manager.update_progress(sent_count, failed_count, idx, email, "Delivered" if success else "Failed")

        # Buffer delay between emails
        if idx < total and not manager.stop_requested:
            wait_sec = random.uniform(min_delay, max_delay)
            manager.add_log(f"⏳ Pausing {wait_sec:.1f}s buffer delay to safeguard primary inbox placement...")
            time.sleep(wait_sec)

    if smtp:
        try:
            smtp.quit()
        except Exception:
            pass

    # Update final campaign status in DB
    c.execute("""
    UPDATE campaigns
    SET sent_count = ?, status = ?
    WHERE id = ?
    """, (sent_count, "completed" if not manager.stop_requested else "stopped", campaign_id))
    conn.commit()
    conn.close()

    if not manager.stop_requested:
        manager.finish("completed", f"🎉 Campaign completed! Successfully delivered {sent_count}/{total} emails.")


# HTTP Server Handler
class AppRequestHandler(BaseHTTPRequestHandler):
    current_attachment = None  # { filename, bytes, subtype }

    def log_message(self, format, *args):
        # Silence default stderr logging for clean console
        return

    def send_json(self, data, status=200):
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()
        self.wfile.write(json.dumps(data).encode("utf-8"))

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path

        if path in ("/", "/index.html", "/api/index.py", "/api"):
            index_path = os.path.join(WEB_DIR, "index.html")
            if os.path.exists(index_path):
                with open(index_path, "rb") as f:
                    content = f.read()
                self.send_response(200)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.end_headers()
                self.wfile.write(content)
            else:
                self.send_response(404)
                self.end_headers()
                self.wfile.write(b"UI file not found.")
            return

        if path == "/api/config":
            cfg = load_config()
            cfg["has_attachment"] = bool(AppRequestHandler.current_attachment)
            cfg["attachment_name"] = AppRequestHandler.current_attachment.get("filename") if AppRequestHandler.current_attachment else ""
            self.send_json(cfg)
            return

        if path == "/api/status":
            with manager.lock:
                self.send_json(manager.status)
            return

        if path == "/api/templates":
            conn = sqlite3.connect(DB_PATH)
            c = conn.cursor()
            rows = c.execute("SELECT id, name, subject, body, is_default FROM templates ORDER BY id ASC").fetchall()
            conn.close()
            templates = [
                {"id": r[0], "name": r[1], "subject": r[2], "body": r[3], "is_default": bool(r[4])}
                for r in rows
            ]
            self.send_json({"templates": templates})
            return

        if path == "/api/campaigns":
            conn = sqlite3.connect(DB_PATH)
            c = conn.cursor()
            rows = c.execute("""
            SELECT id, title, created_at, source_type, source_name, subject, body_template, total_recipients, sent_count, status
            FROM campaigns ORDER BY id DESC LIMIT 50
            """).fetchall()
            conn.close()

            campaigns = []
            for r in rows:
                campaigns.append({
                    "id": r[0],
                    "title": r[1],
                    "created_at": r[2],
                    "source_type": r[3],
                    "source_name": r[4],
                    "subject": r[5],
                    "body_template": r[6],
                    "total_recipients": r[7],
                    "sent_count": r[8],
                    "status": r[9]
                })
            self.send_json({"campaigns": campaigns})
            return

        if path.startswith("/api/campaigns/"):
            camp_id = path.split("/")[-1]
            conn = sqlite3.connect(DB_PATH)
            c = conn.cursor()
            camp = c.execute("""
            SELECT id, title, created_at, source_type, source_name, subject, body_template, total_recipients, sent_count, status
            FROM campaigns WHERE id = ?
            """, (camp_id,)).fetchone()

            recipients = []
            if camp:
                recs = c.execute("""
                SELECT email, name, data_json, status, sent_at
                FROM campaign_recipients WHERE campaign_id = ?
                """, (camp_id,)).fetchall()
                for rc in recs:
                    recipients.append({
                        "email": rc[0],
                        "name": rc[1],
                        "data": json.loads(rc[2]) if rc[2] else {},
                        "status": rc[3],
                        "sent_at": rc[4]
                    })
            conn.close()

            if camp:
                self.send_json({
                    "campaign": {
                        "id": camp[0],
                        "title": camp[1],
                        "created_at": camp[2],
                        "source_type": camp[3],
                        "source_name": camp[4],
                        "subject": camp[5],
                        "body_template": camp[6],
                        "total_recipients": camp[7],
                        "sent_count": camp[8],
                        "status": camp[9]
                    },
                    "recipients": recipients
                })
            else:
                self.send_json({"error": "Campaign not found"}, status=404)
            return

        self.send_response(404)
        self.end_headers()

    def do_POST(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path

        content_length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(content_length)

        if path == "/api/config":
            try:
                data = json.loads(body)
                save_config(data)
                self.send_json({"success": True, "config": load_config()})
            except Exception as e:
                self.send_json({"error": str(e)}, status=400)
            return

        if path == "/api/parse-google-sheet":
            try:
                data = json.loads(body)
                sheet_url = data.get("url", "").strip()
                if not sheet_url:
                    return self.send_json({"error": "Google Sheet URL is required"}, status=400)

                raw_headers, clean_keys, records = fetch_google_sheet(sheet_url)
                if not records:
                    return self.send_json({"error": "No records found in Google Sheet"}, status=400)

                fields = identify_fields(clean_keys, records)
                self.send_json({
                    "success": True,
                    "source": "google_sheet",
                    "source_name": sheet_url,
                    "attributes": clean_keys,
                    "raw_headers": raw_headers,
                    "fields": fields,
                    "total_rows": len(records),
                    "sample": records[:5],
                    "all_records": records
                })
            except Exception as e:
                self.send_json({"error": f"Failed to fetch Google Sheet: {e}. Please ensure link sharing is set to 'Anyone with the link can view'."}, status=400)
            return

        if path == "/api/parse-excel":
            try:
                data = json.loads(body)
                file_b64 = data.get("file_base64", "")
                filename = data.get("filename", "upload.xlsx")

                if file_b64:
                    file_bytes = base64.b64decode(file_b64)
                    raw_headers, clean_keys, records = parse_excel_file(file_bytes)
                elif os.path.exists(os.path.join(BASE_DIR, filename)):
                    # Load from workspace file
                    with open(os.path.join(BASE_DIR, filename), "rb") as f:
                        file_bytes = f.read()
                    raw_headers, clean_keys, records = parse_excel_file(file_bytes)
                else:
                    return self.send_json({"error": "No Excel file provided or found"}, status=400)

                if not records:
                    return self.send_json({"error": "No data rows found in Excel sheet"}, status=400)

                fields = identify_fields(clean_keys, records)
                self.send_json({
                    "success": True,
                    "source": "excel",
                    "source_name": filename,
                    "attributes": clean_keys,
                    "raw_headers": raw_headers,
                    "fields": fields,
                    "total_rows": len(records),
                    "sample": records[:5],
                    "all_records": records
                })
            except Exception as e:
                self.send_json({"error": f"Failed to parse Excel file: {e}"}, status=400)
            return

        if path == "/api/upload-attachment":
            try:
                data = json.loads(body)
                filename = data.get("filename", "attachment")
                file_b64 = data.get("file_base64", "")
                if file_b64:
                    AppRequestHandler.current_attachment = {
                        "filename": filename,
                        "bytes": base64.b64decode(file_b64),
                        "subtype": "pdf" if filename.lower().endswith(".pdf") else "octet-stream"
                    }
                    self.send_json({"success": True, "filename": filename})
                else:
                    self.send_json({"error": "Empty attachment file"}, status=400)
            except Exception as e:
                self.send_json({"error": str(e)}, status=400)
            return

        if path == "/api/delete-attachment":
            AppRequestHandler.current_attachment = None
            self.send_json({"success": True, "message": "Attachment detached."})
            return

        if path == "/api/preview":
            try:
                data = json.loads(body)
                subject_tpl = data.get("subject", "")
                body_tpl = data.get("body", "")
                contacts = data.get("contacts", [])[:3]

                previews = []
                for c in contacts:
                    previews.append({
                        "recipient": c.get("email") or c.get("name") or "Contact",
                        "subject": render_template(subject_tpl, c),
                        "body": render_template(body_tpl, c)
                    })
                self.send_json({"previews": previews})
            except Exception as e:
                self.send_json({"error": str(e)}, status=400)
            return

        if path == "/api/templates":
            try:
                data = json.loads(body)
                name = data.get("name", "").strip() or "Custom Template"
                subject = data.get("subject", "")
                body_content = data.get("body", "")
                if not body_content:
                    return self.send_json({"error": "Template body cannot be empty"}, status=400)

                conn = sqlite3.connect(DB_PATH)
                c = conn.cursor()
                c.execute("INSERT INTO templates (name, subject, body, is_default) VALUES (?, ?, ?, 0)", (name, subject, body_content))
                template_id = c.lastrowid
                conn.commit()
                conn.close()

                self.send_json({"success": True, "template": {"id": template_id, "name": name, "subject": subject, "body": body_content, "is_default": False}})
            except Exception as e:
                self.send_json({"error": str(e)}, status=400)
            return

        if path == "/api/delete-template":
            try:
                data = json.loads(body)
                template_id = data.get("id")
                conn = sqlite3.connect(DB_PATH)
                c = conn.cursor()
                c.execute("DELETE FROM templates WHERE id = ? AND is_default = 0", (template_id,))
                conn.commit()
                conn.close()
                self.send_json({"success": True})
            except Exception as e:
                self.send_json({"error": str(e)}, status=400)
            return

        if path == "/api/prepare-queue":
            try:
                data = json.loads(body)
                subject_tpl = data.get("subject", "")
                body_tpl = data.get("body", "")
                recipients = data.get("recipients", [])

                queue = []
                for idx, r in enumerate(recipients):
                    email = r.get("email", "").strip()
                    name = r.get("name", "").strip()
                    if not name and r.get("pura_name"):
                        name = r.get("pura_name").split()[0]
                    rendered_subj = render_template(subject_tpl, r)
                    rendered_body = render_template(body_tpl, r)
                    queue.append({
                        "id": idx,
                        "email": email,
                        "name": name,
                        "data": r,
                        "subject": rendered_subj,
                        "body": rendered_body,
                        "status": "pending",  # 'approved', 'skipped', 'pending'
                        "skipped": False,
                        "edited": False
                    })
                self.send_json({"queue": queue, "total": len(queue)})
            except Exception as e:
                self.send_json({"error": str(e)}, status=400)
            return

        if path == "/api/test-smtp":
            try:
                data = json.loads(body)
                email = str(data.get("sender_email", "")).strip()
                pw = str(data.get("app_password", "")).replace(" ", "").strip()
                server = data.get("smtp_server", "smtp.gmail.com")
                port = int(data.get("smtp_port", 465))

                if not email or not pw:
                    return self.send_json({"error": "Please enter both your Gmail address and 16-character App Password."}, status=400)

                test_smtp = smtplib.SMTP_SSL(server, port, timeout=12)
                test_smtp.login(email, pw)
                test_smtp.quit()
                self.send_json({"success": True, "message": f"Successfully connected as {email}!"})
            except smtplib.SMTPAuthenticationError as e:
                self.send_json({"error": "Gmail authentication failed. Please make sure you are using a 16-character Gmail App Password (not your normal Google account password) with 2-Step Verification enabled."}, status=401)
            except Exception as e:
                self.send_json({"error": f"Connection failed: {e}"}, status=400)
            return

        if path == "/api/delete-campaign":
            try:
                data = json.loads(body)
                camp_id = data.get("id")
                conn = sqlite3.connect(DB_PATH)
                c = conn.cursor()
                c.execute("DELETE FROM campaign_recipients WHERE campaign_id = ?", (camp_id,))
                c.execute("DELETE FROM campaigns WHERE id = ?", (camp_id,))
                conn.commit()
                conn.close()
                self.send_json({"success": True})
            except Exception as e:
                self.send_json({"error": str(e)}, status=400)
            return

        if path == "/api/send":
            try:
                data = json.loads(body)
                title = data.get("title", f"Campaign {time.strftime('%Y-%m-%d %H:%M')}")
                source_type = data.get("source_type", "excel")
                source_name = data.get("source_name", "Sheet")
                subject_tpl = data.get("subject", "")
                body_tpl = data.get("body", "")
                recipients = data.get("recipients", [])
                cfg = load_config()
                if data.get("sender_email"):
                    cfg["sender_email"] = str(data["sender_email"]).strip()
                if data.get("app_password"):
                    cfg["app_password"] = str(data["app_password"]).replace(" ", "").strip()
                if data.get("sender_name"):
                    cfg["sender_name"] = str(data["sender_name"]).strip()

                dry_run_req = data.get("dry_run")
                dry_run = bool(dry_run_req) if dry_run_req is not None else cfg.get("dry_run", DRY_RUN)

                if not recipients:
                    return self.send_json({"error": "No recipients provided for campaign"}, status=400)

                with manager.lock:
                    if manager.status["state"] == "sending":
                        return self.send_json({"error": "A campaign is already running."}, status=400)

                # Create campaign entry in DB
                conn = sqlite3.connect(DB_PATH)
                c = conn.cursor()
                att_name = AppRequestHandler.current_attachment.get("filename") if AppRequestHandler.current_attachment else ""
                c.execute("""
                INSERT INTO campaigns (title, source_type, source_name, subject, body_template, attachment_name, total_recipients, sent_count, status)
                VALUES (?, ?, ?, ?, ?, ?, ?, 0, 'sending')
                """, (title, source_type, source_name, subject_tpl, body_tpl, att_name, len(recipients)))
                campaign_id = c.lastrowid
                conn.commit()
                conn.close()

                manager.reset_status(campaign_id, title, len(recipients))

                t = threading.Thread(
                    target=send_campaign_worker,
                    args=(campaign_id, cfg, subject_tpl, body_tpl, recipients, AppRequestHandler.current_attachment, dry_run),
                    daemon=True
                )
                manager.active_thread = t
                t.start()

                self.send_json({"success": True, "campaign_id": campaign_id, "total": len(recipients)})
            except Exception as e:
                self.send_json({"error": str(e)}, status=400)
            return

        if path == "/api/stop":
            manager.request_stop()
            self.send_json({"success": True, "message": "Stop signal sent."})
            return

        self.send_response(404)
        self.end_headers()


class ThreadingHTTPServer(socketserver.ThreadingMixIn, HTTPServer):
    daemon_threads = True
    allow_reuse_address = True


def find_free_port(start_port=5000):
    for port in range(start_port, start_port + 20):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            if s.connect_ex(("127.0.0.1", port)) != 0:
                return port
    return start_port


def start_server(port=None, host=None, auto_open=True):
    env_port = os.environ.get("PORT")
    selected_port = port or (int(env_port) if env_port else find_free_port(5000))
    selected_host = host or os.environ.get("HOST", "0.0.0.0")

    server = ThreadingHTTPServer((selected_host, selected_port), AppRequestHandler)
    display_host = "localhost" if selected_host in ("0.0.0.0", "127.0.0.1") else selected_host
    url = f"http://{display_host}:{selected_port}"

    print("=" * 60)
    print("🚀 Job Application & Campaign Mailer Web App")
    print("=" * 60)
    print(f"👉 Web Server Running at: {url} (Bound to {selected_host}:{selected_port})")
    print("Press Ctrl+C to stop the server.")
    print("=" * 60)

    # Only auto-open browser in local desktop runs, not headless cloud environments
    if auto_open and not env_port:
        def open_browser():
            time.sleep(1.0)
            try:
                webbrowser.open(url)
            except Exception:
                pass
        threading.Thread(target=open_browser, daemon=True).start()

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopping server...")
        server.server_close()


# ============================================================
# VERCEL / SERVERLESS / WSGI ENTRYPOINTS
# Vercel scans Python files for top-level "app", "application",
# or "handler" (BaseHTTPRequestHandler subclass)
# ============================================================
handler = AppRequestHandler
app = AppRequestHandler
application = AppRequestHandler


if __name__ == "__main__":
    start_server(auto_open=True)
