#!/usr/bin/env python3
"""
Verification script for context receipts.
This script checks the SHA-256 hashes of the files referenced in a context_receipt.json
against the actual files on disk.
"""

import sys
import os
import json
import hashlib

def calculate_sha256(file_path):
    """Calculates the SHA-256 hash of a file."""
    hasher = hashlib.sha256()
    try:
        with open(file_path, 'rb') as f:
            for chunk in iter(lambda: f.read(65536), b""):
                hasher.update(chunk)
    except FileNotFoundError:
        return None, f"File not found: {file_path}"
    except Exception as e:
        return None, f"Error reading file {file_path}: {e}"
    return hasher.hexdigest().lower(), None

def main():
    if len(sys.argv) < 2:
        print("[ERROR] Please provide the path to context_receipt.json as a command-line argument.")
        print("Usage: python verify_context_receipt.py <path_to_context_receipt.json>")
        sys.exit(1)

    receipt_path = sys.argv[1]
    if not os.path.exists(receipt_path):
        print(f"[ERROR] Context receipt file not found: {receipt_path}")
        sys.exit(1)

    try:
        with open(receipt_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except json.JSONDecodeError as e:
        print(f"[ERROR] Format error: {receipt_path} is not a valid JSON file. {e}")
        sys.exit(1)
    except Exception as e:
        print(f"[ERROR] Failed to read {receipt_path}: {e}")
        sys.exit(1)

    # Accept 'receipts' or common fallbacks like 'loaded_specs', 'fingerprints', 'files_loaded', or 'spec_files'
    receipts = data.get("receipts")
    if receipts is None:
        receipts = data.get("loaded_specs")
    if receipts is None:
        receipts = data.get("fingerprints")
    if receipts is None:
        receipts = data.get("files_loaded")
    
    if receipts is None and "spec_files" in data:
        spec_files = data["spec_files"]
        if isinstance(spec_files, list):
            receipts = {}
            for item in spec_files:
                if isinstance(item, dict) and "path" in item and "sha256" in item:
                    # Strip workspace prefix if absolute path is stored
                    path_val = item["path"]
                    # If it starts with C:\AI_Facepost, make it relative
                    if path_val.lower().startswith("c:\\ai_facepost\\"):
                        path_val = path_val[15:]
                    elif path_val.lower().startswith("c:/ai_facepost/"):
                        path_val = path_val[15:]
                    receipts[path_val] = item["sha256"]

    if receipts is None:
        print(f"[ERROR] Format error: JSON in {receipt_path} does not contain 'receipts', 'loaded_specs', 'fingerprints', 'files_loaded', or 'spec_files' key.")
        sys.exit(1)

    if not isinstance(receipts, dict):
        print(f"[ERROR] Format error: 'receipts' or 'loaded_specs' in {receipt_path} must be a dictionary mapping file paths to hashes.")
        sys.exit(1)

    # Determine workspace root: default to C:\AI_Facepost, fallback to script parent levels if needed
    workspace_root = os.path.abspath(r"C:\AI_Facepost")
    if not os.path.isdir(workspace_root):
        # Resolve 3 levels up from this script (verify_context_receipt.py is in agent_harness/harness/)
        script_dir = os.path.dirname(os.path.abspath(__file__))
        workspace_root = os.path.abspath(os.path.join(script_dir, "..", ".."))

    all_matched = True

    for spec_rel_path, expected_hash in receipts.items():
        # Normalize file path for cross-platform compatibility
        normalized_rel_path = spec_rel_path.replace("/", os.sep).replace("\\", os.sep)
        full_path = os.path.abspath(os.path.join(workspace_root, normalized_rel_path))

        calculated_hash, err = calculate_sha256(full_path)
        if err:
            print(f"[ERROR] Missing or unreadable file: {spec_rel_path}")
            print(f"  Reason: {err}")
            sys.exit(1)

        expected_hash_clean = expected_hash.strip().lower()
        if calculated_hash != expected_hash_clean:
            print(f"[ERROR] Hash mismatch for spec file: {spec_rel_path}")
            print(f"  Expected: {expected_hash_clean}")
            print(f"  Got:      {calculated_hash}")
            all_matched = False

    if not all_matched:
        sys.exit(1)

    print("[SUCCESS] All context receipts verified.")
    sys.exit(0)

if __name__ == "__main__":
    main()
