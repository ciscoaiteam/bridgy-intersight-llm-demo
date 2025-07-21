#!/usr/bin/env python3
# MongoDB compatibility fix for motor and pymongo
import sys
import os

def apply_mongodb_compatibility_patch():
    print("⚠️ Applying motor/pymongo compatibility patch")
    
    # Create the missing variable in pymongo.cursor
    import pymongo.cursor
    if not hasattr(pymongo.cursor, "_QUERY_OPTIONS"):
        pymongo.cursor._QUERY_OPTIONS = frozenset([
            "tailable_cursor", "secondary_ok", "oplog_replay",
            "no_timeout", "await_data", "exhaust", "partial"
        ])
        print("✅ Added _QUERY_OPTIONS to pymongo.cursor")
    else:
        print("✅ _QUERY_OPTIONS already exists in pymongo.cursor")

def fix_python_paths():
    # Ensure bridgy_main is importable
    if not os.path.exists("/app/bridgy_main"):
        try:
            os.symlink("/app/bridgy-main", "/app/bridgy_main")
            print("✅ Created bridgy_main module link")
        except Exception as e:
            print(f"⚠️ Could not create bridgy_main module link: {e}")
    
    # Make sure Python path is set correctly
    for path in ["/app", "/app/bridgy-main", "/app/bridgy_main"]:
        if path not in sys.path:
            sys.path.append(path)
            print(f"✅ Added {path} to Python path")

def fix_env_file():
    # Create direct copy of .env at /app/.env if it doesn't exist
    if os.path.exists("/app/bridgy-main/.env") and not os.path.exists("/app/.env"):
        try:
            from shutil import copyfile
            copyfile("/app/bridgy-main/.env", "/app/.env")
            print("✅ Copied .env file to /app/.env")
        except Exception as e:
            print(f"⚠️ Could not copy .env file: {e}")

if __name__ == "__main__":
    apply_mongodb_compatibility_patch()
    fix_python_paths()
    fix_env_file()
    print("✅ MongoDB compatibility checks completed")
