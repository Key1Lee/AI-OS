#!/usr/bin/env python3
import argparse
from pathlib import Path

import uvicorn

from quality_system.api import create_app

parser = argparse.ArgumentParser()
parser.add_argument("--port", type=int, default=8082)
args = parser.parse_args()
root = Path(__file__).resolve().parents[1]
web = root / "web/dist"
if not (web / "index.html").exists():
    parser.error("Build the interface first: npm --prefix web run build")
uvicorn.run(create_app(web), host="127.0.0.1", port=args.port, log_level="warning")
