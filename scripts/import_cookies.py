#!/usr/bin/env python3
"""
Helper script to convert browser cookies to Playwright storage_state format.

Usage:
    1. Export cookies from Firefox (Cookie-Editor addon) as JSON
    2. Run: python scripts/import_cookies.py cookies.json
    3. This generates idealista_state.json compatible with Playwright
"""

import json
import sys
from pathlib import Path
import time

def convert_cookie_to_playwright(cookie):
    """Convert simple cookie dict to Playwright format."""
    pw_cookie = {
        "name": cookie.get("name", ""),
        "value": cookie.get("value", ""),
        "domain": cookie.get("domain", ".idealista.com"),
        "path": cookie.get("path", "/"),
    }
    
    # Add optional fields if present
    if "expires" in cookie:
        pw_cookie["expires"] = cookie["expires"]
    else:
        # Default: expires in 24 hours
        pw_cookie["expires"] = time.time() + 86400
    
    if "httpOnly" in cookie:
        pw_cookie["httpOnly"] = cookie["httpOnly"]
    if "secure" in cookie:
        pw_cookie["secure"] = cookie["secure"]
    if "sameSite" in cookie:
        pw_cookie["sameSite"] = cookie["sameSite"]
    
    return pw_cookie

def convert_cookies_json(input_file):
    """Read simple cookies JSON and convert to Playwright format."""
    with open(input_file, 'r') as f:
        cookies = json.load(f)
    
    # Handle different export formats
    if isinstance(cookies, dict) and "cookies" in cookies:
        # Netscape format or similar
        cookies = cookies["cookies"]
    elif not isinstance(cookies, list):
        print(f"Error: Expected list or dict with 'cookies' key, got {type(cookies)}")
        sys.exit(1)
    
    # Convert each cookie
    pw_cookies = [convert_cookie_to_playwright(c) for c in cookies]
    
    # Build storage state format
    storage_state = {
        "cookies": pw_cookies,
        "origins": []
    }
    
    return storage_state

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python scripts/import_cookies.py <cookies.json>")
        print("\nExample:")
        print("  1. Export cookies from Firefox with Cookie-Editor addon")
        print("  2. Save to cookies.json")
        print("  3. Run: python scripts/import_cookies.py cookies.json")
        print("  4. Check idealista_state.json")
        sys.exit(1)
    
    input_file = sys.argv[1]
    
    if not Path(input_file).exists():
        print(f"Error: File {input_file} not found")
        sys.exit(1)
    
    print(f"Converting cookies from {input_file}...")
    
    try:
        storage_state = convert_cookies_json(input_file)
        
        output_file = "idealista_state.json"
        with open(output_file, 'w') as f:
            json.dump(storage_state, f, indent=2)
        
        print(f"✅ Success! Saved to {output_file}")
        print(f"   Cookies imported: {len(storage_state['cookies'])}")
        
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)
