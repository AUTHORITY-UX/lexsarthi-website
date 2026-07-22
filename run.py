#!/usr/bin/env python3
# run.py - Start Unknown Verdict with Verdict Engine

import os
import sys
import asyncio
import argparse
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

def main():
    parser = argparse.ArgumentParser(description="Unknown Verdict - Verdict Engine")
    parser.add_argument(
        "--mode",
        choices=["sports", "hybrid", "eco"],
        default="hybrid",
        help="Engine mode: sports (fastest), hybrid (balanced), eco (energy saving)"
    )
    
    args = parser.parse_args()
    
    # Import app
    from app import app
    
    # Import engine
    from verdict_engine import start_verdict_engine
    
    print(f"""
    ════════════════════════════════════════════════════════════════
      🏎️  UNKNOWN VERDICT - VERDICT ENGINE
    
      Mode: {args.mode.upper()}
      Server: http://0.0.0.0:7860
      Press CTRL+C to stop
    ════════════════════════════════════════════════════════════════
    """)
    
    asyncio.run(start_verdict_engine(app, mode=args.mode))

if __name__ == "__main__":
    main()