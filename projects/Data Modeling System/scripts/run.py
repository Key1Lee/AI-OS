"""Serve the independently built UI and API from one loopback origin."""

import argparse
from pathlib import Path

import uvicorn

from data_modeling_lab.api import create_app

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", type=int, default=8075)
    parser.add_argument("--api-only", action="store_true")
    args = parser.parse_args()
    web_dir = None if args.api_only else Path(__file__).resolve().parents[1] / "apps" / "web" / "dist"
    uvicorn.run(create_app(web_dir=web_dir), host="127.0.0.1", port=args.port)
