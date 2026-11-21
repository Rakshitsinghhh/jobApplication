#!/usr/bin/env python3
"""
Mail Campaigner & Follow-Up Dispatcher
Entry point for launching the Web UI or optional CLI mode.
"""

import sys
from app import AppRequestHandler, start_server, load_config

# ============================================================
# VERCEL / SERVERLESS ENTRYPOINTS
# Vercel scans root .py files and requires a top-level
# "app", "application", or "handler" variable.
# ============================================================
handler = AppRequestHandler
app = AppRequestHandler
application = AppRequestHandler

DRY_RUN = False


def main():
    if "--cli" in sys.argv:
        print("Launching in CLI mode...")
        cfg = load_config()
        print(f"Loaded configuration for {cfg.get('sender_email')}")
    else:
        start_server(auto_open=True)


if __name__ == "__main__":
    main()
