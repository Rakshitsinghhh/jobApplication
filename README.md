# Check Box — Smart Outreach & Mail Campaigner

A high-performance, dark-mode email outreach dashboard with a **1-by-1 Human Verification Review Queue**, multi-source contact loading (Excel/CSV and Google Sheets), custom template structures, past campaign retrieval, anti-spam buffer delays, and seamless **one-click web deployment**.

---

## 🌟 Highlights

- **🔒 Zero Stored Credentials**: No passwords or emails are hardcoded in the codebase. Web users securely input their Gmail address and 16-character Google App Password directly in the UI modal.
- **⚡ Automatic Space Stripping**: Google displays App Passwords with spaces (`abcd efgh ijkl mnop`). Check Box automatically removes all spaces in both the UI and backend (`abcdefghijklmnop`).
- **🧪 Live SMTP Connection Tester**: Test your Gmail SMTP connection live from the UI before launching any outreach.
- **📂 New Campaign vs Past Campaign Retrieval**:
  - **New Campaign**: Upload Excel (`.xlsx`), CSV files, or fetch directly from live Google Sheets.
  - **Past Campaign Retrieval**: Browse historical campaigns stored in SQLite (`campaigns.db`), inspect delivery metrics, and reload previous recipients + templates into the review queue for follow-ups.
- **👤 1-by-1 Human Verification Layer**:
  - Review and proofread every personalized email individually before dispatch.
  - Approve (`✓ Approve & Next` or press `Enter`) or Skip (`✕ Skip` or press `S`).
  - Inline editing: customize subject or body text for specific contacts on the fly.
  - Visual recipient timeline pills for quick navigation.
- **🎨 Check Box Obsidian Dark Theme**: Designed after modern developer dashboards with slate containers, neon lime (`#b4f23e`), and sunset orange (`#ff9431`) status indicators.
- **🛡️ Anti-Spam Buffer Protection**: Configured with a randomized 3–4 second delay between sends to protect sender domain reputation and ensure Primary inbox delivery.
- **🧪 Dry Run Simulation Mode**: Test entire campaigns safely without sending real emails.
- **☁️ 100% Web & Cloud Ready**: Zero external web frameworks (built on pure Python standard library HTTP server + `openpyxl`). Ready to deploy to **Render**, **Railway**, **Fly.io**, **Heroku**, or **Docker**.

---

## 🚀 Quick Start (Local)

### 1. Run Setup & Start Direct
```bash
# On Linux / macOS:
./setup.sh
# (Creates the virtualenv, installs openpyxl, and immediately launches the app)

# Or launch anytime using:
./run.sh

# On Windows:
setup.bat
```

### 2. Manual Launch
```bash
source venv/bin/activate
python main.py
```
Open your browser at: **`http://localhost:5000`**

---

## 🌐 Web & Cloud Deployment

Check Box is designed to be deployed online as a shared web tool. Any user opening your deployed URL can enter their own Gmail and App Password into the UI modal to run their campaigns.

### Deploying to Render
1. Push your repository to GitHub or GitLab.
2. In [Render Dashboard](https://dashboard.render.com), click **New +** > **Web Service**.
3. Connect your repository.
4. Settings:
   - **Environment**: `Python 3`
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `python app.py`
5. Click **Create Web Service**. Render automatically assigns the `PORT` and provides a live HTTPS URL.

### Deploying to Railway
1. Go to [Railway.app](https://railway.app) and select **New Project** > **Deploy from GitHub repo**.
2. Railway will automatically detect the `Procfile` / `Dockerfile` and deploy the service.

### Deploying with Docker
```bash
# Build the Docker image
docker build -t check-box-mail .

# Run the container (maps port 5000)
docker run -p 5000:5000 check-box-mail
```
Access at `http://localhost:5000`.

---

## 🔑 How to Get a Gmail App Password

Google requires an **App Password** for secure SMTP sending:

1. Visit your [Google Account Security](https://myaccount.google.com/security) settings.
2. Ensure **2-Step Verification** is enabled on your account.
3. Open [Google App Passwords](https://myaccount.google.com/apppasswords).
4. Enter an App Name (e.g. `Mail Campaigner`) and click **Create**.
5. Copy the 16-character password (e.g. `abcd efgh ijkl mnop`).
6. In Check Box, click the **Connect Gmail** pill (top right) or the **⚙️** icon, paste your email and password, and click **⚡ Test Connection**.
   *(Note: Spaces are automatically stripped for you!)*

---

## 📋 How It Works (Step-by-Step)

### Step 1: Choose Source
- **New Campaign**:
  - **Upload Excel / CSV**: Drag and drop your `.xlsx` or `.csv` file, or click *"Load 'mailing delhi ncr.xlsx'"*.
  - **Google Sheet Link**: Paste a public/shareable Google Sheet URL and click **Fetch**.
- **Retrieve Past Campaign**:
  - View all past campaigns with sent/total stats and timestamps.
  - Click **📥 Retrieve & Load Contacts** to load previous contacts and templates back into the workspace.

### Step 2: Compose Template & Placeholders
- Select from pre-loaded structure templates (*Thank You & Networking*, *Job Application / SDE Role*, *Quick Follow-Up*, *Coffee Chat*) or click **➕ Add / Save Template** to create your own.
- Click placeholder buttons (e.g. `+ {{name}}`, `+ {{company}}`) to dynamically insert fields into your body or subject.
- Attach files (resumes, portfolios) using **📎 Attach Resume / File**.

### Step 3: Human Verification Layer (1-by-1 Review Queue)
- Click **Proceed to Human Review (1-by-1) →**.
- Every single rendered email is presented individually with actual recipient data inserted.
- **Keyboard Shortcuts**:
  - `Enter` : Approve & proceed to next email.
  - `S` : Skip recipient (exclude from send).
  - `←` / `→` : Navigate previous/next email.
- You can freely edit the subject or body for specific recipients before approving.

### Step 4: Dispatch & Live Monitoring
- Click **🚀 Send Campaign Now**.
- In **Final Mailing** mode, emails are delivered via Gmail SMTP with anti-spam buffer delays.
- In **Dry Run** mode, sending is simulated without delivering live emails.
- Watch live real-time progress ratios, percentage bars, and timestamped delivery logs.

---

## 📁 Repository Structure

```
jobApplication/
├── app.py                  # Web server, SQLite storage, and background SMTP dispatcher
├── main.py                 # Local launcher (starts server & opens browser)
├── web/
│   └── index.html          # Single-page Check Box dashboard UI
├── Dockerfile              # Container definition for cloud deployments
├── Procfile                # Heroku/Render/Railway process file
├── .dockerignore           # Excludes local files from Docker builds
├── config.json             # Optional local credentials store (blank by default)
├── campaigns.db            # SQLite database tracking campaigns & history
├── mailing delhi ncr.xlsx  # Sample contact list
├── requirements.txt        # Minimal dependencies (openpyxl)
├── run.sh                  # Quick Linux/macOS launcher
├── setup.sh                # Setup script for Linux/macOS
├── setup.bat               # Setup script for Windows
└── README.md               # Documentation
```
