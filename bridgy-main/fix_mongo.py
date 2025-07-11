#!/usr/bin/env python3
"""
MongoDB driver compatibility fix module.
This module patches pymongo.cursor to add _QUERY_OPTIONS if it's missing.
This fixes the "cannot import name '_QUERY_OPTIONS'" error that occurs when
a new version of pymongo is used with an older version of motor.
"""
import sys
import os
import inspect

def apply_pymongo_patch():
    """
    Apply patch to pymongo.cursor to add _QUERY_OPTIONS.
    Returns True if patch was applied successfully.
    """
    try:
        # First try to import it - if it works, no patch needed
        try:
            from pymongo.cursor import _QUERY_OPTIONS
            print("✅ PyMongo compatibility check passed (_QUERY_OPTIONS exists)")
            return True
        except ImportError:
            pass
            
        print("⚠️ Applying PyMongo patch to add _QUERY_OPTIONS")
        
        # Import the module that needs patching
        import pymongo.cursor
        
        # Define the missing constant if it doesn't exist
        if not hasattr(pymongo.cursor, "_QUERY_OPTIONS"):
            pymongo.cursor._QUERY_OPTIONS = frozenset([
                "tailable_cursor", "secondary_ok", "oplog_replay",
                "no_timeout", "await_data", "exhaust", "partial"
            ])
            print("✅ Successfully added _QUERY_OPTIONS to pymongo.cursor")
            return True
        else:
            print("✅ _QUERY_OPTIONS already exists in pymongo.cursor")
            return True
    except Exception as e:
        print(f"❌ Failed to apply PyMongo patch: {e}")
        return False

def setup_bridgy_module():
    """
    Ensure bridgy_main is available as a module.
    """
    try:
        # Create symlink if it doesn't exist
        if not os.path.exists("/app/bridgy_main"):
            try:
                os.symlink("/app/bridgy-main", "/app/bridgy_main")
                # Create __init__.py to make it a valid Python package
                with open("/app/bridgy_main/__init__.py", "w") as f:
                    pass
                print("✅ Created bridgy_main module link")
            except Exception as e:
                print(f"⚠️ Could not create bridgy_main module link: {e}")
        
        # Add paths to sys.path
        for path in ["/app", "/app/bridgy-main", "/app/bridgy_main"]:
            if path not in sys.path:
                sys.path.append(path)
        
        return True
    except Exception as e:
        print(f"❌ Failed to set up bridgy_main module: {e}")
        return False

def fix_env_file():
    """
    Ensure .env file exists in the expected locations.
    """
    try:
        # Check if we need to create a copy at /app/.env
        if os.path.exists("/app/bridgy-main/.env") and not os.path.exists("/app/.env"):
            try:
                # Try creating a symlink first
                try:
                    os.symlink("/app/bridgy-main/.env", "/app/.env")
                    print("✅ Created symlink from /app/bridgy-main/.env to /app/.env")
                except:
                    # If symlink fails, copy the file
                    from shutil import copyfile
                    copyfile("/app/bridgy-main/.env", "/app/.env")
                    print("✅ Copied .env file to /app/.env")
                return True
            except Exception as e:
                print(f"⚠️ Could not create .env at /app/.env: {e}")
        return True
    except Exception as e:
        print(f"⚠️ Error checking .env files: {e}")
        return False

def run_all_fixes():
    """Run all compatibility fixes and print results."""
    print("\n=== Running MongoDB Compatibility Fixes ===")
    mongo_result = apply_pymongo_patch()
    
    print("\n=== Setting Up Python Module Structure ===")
    module_result = setup_bridgy_module()
    
    print("\n=== Fixing Environment Files ===")
    env_result = fix_env_file()
    
    print("\n=== Fix Summary ===")
    if all([mongo_result, module_result, env_result]):
        print("✅ All fixes applied successfully")
    else:
        failed = []
        if not mongo_result: failed.append("MongoDB patch")
        if not module_result: failed.append("Module setup")
        if not env_result: failed.append("Environment files")
        print(f"⚠️ Some fixes failed: {', '.join(failed)}")
    
    # Return success status
    return all([mongo_result, module_result, env_result])

if __name__ == "__main__":
    run_all_fixes()
