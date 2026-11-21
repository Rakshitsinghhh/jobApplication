#!/usr/bin/env python3
"""
Mail Campaigner & Follow-Up Dispatcher
Entry point for launching the Web UI or optional CLI mode.
"""

import sys
import app

# ============================================================
# DRY RUN TOGGLE
# If True : DRY RUN mode (simulates everything, no real emails sent)
# If False: FINAL MAILING mode (sends real emails via Gmail SMTP)
# ============================================================
DRY_RUN = False
app.DRY_RUN = DRY_RUN

def main():
    if "--cli" in sys.argv:
        print("Launching in CLI mode...")
        # Optional CLI fallback if requested
        cfg = app.load_config()
        print(f"Loaded configuration for {cfg.get('sender_email')}")
    else:
        # Launch modern interactive web application
        app.start_server(auto_open=True)

if __name__ == "__main__":
    main()
