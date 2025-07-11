#!/usr/bin/env python3
import sys
import importlib
import os

def verify_import(module_name, expected_version=None):
    try:
        module = importlib.import_module(module_name)
        if hasattr(module, "__version__"):
            version = module.__version__
            if expected_version and version != expected_version:
                print(f"⚠️ {module_name} version mismatch: found {version}, expected {expected_version}")
            else:
                print(f"✅ Successfully imported {module_name} (version: {version})")
        else:
            print(f"✅ Successfully imported {module_name} (version unknown)")
        return True
    except ImportError as e:
        print(f"❌ Import error for {module_name}: {e}")
        return False

def verify_mongo_compatibility():
    """Verify that motor and pymongo are compatible"""
    try:
        from pymongo.cursor import _QUERY_OPTIONS
        print("✅ MongoDB compatibility check: _QUERY_OPTIONS found in pymongo.cursor")
    except ImportError:
        print("❌ MongoDB compatibility check: _QUERY_OPTIONS missing from pymongo.cursor")
        try:
            import pymongo
            import motor
            print(f"    pymongo version: {pymongo.__version__}")
            print(f"    motor version: {motor.version}")
            print("    Compatible versions are pymongo==4.5.0 and motor==2.5.1")
        except ImportError as e:
            print(f"    Additional error: {e}")
        return False
    return True

# Add all import paths
sys.path.extend(["/app", "/app/bridgy-main", "/app/bridgy", "/tmp"])

# Check critical modules
critical_modules = [
    "numpy", "scipy", "sklearn", "pypdf", 
    "sentence_transformers", "faiss"
]

# Check MongoDB driver versions specifically
mongo_modules = [
    ("pymongo", "4.5.0"),
    ("motor", "2.5.1")
]

print("\n=== Checking standard modules ===")
for module in critical_modules:
    verify_import(module)

print("\n=== Checking MongoDB driver versions ===")
for module, expected_version in mongo_modules:
    verify_import(module, expected_version)

# Verify MongoDB compatibility
print("\n=== Testing MongoDB driver compatibility ===")
mongo_compatible = verify_mongo_compatibility()

# Try different import paths for bridgy modules
success = False

try:
    from bridgy_main.tools import pdf_loader
    print('✅ Successfully imported pdf_loader via bridgy_main')
    success = True
except ImportError as e:
    print(f'❌ Import error via bridgy_main: {e}')

try:
    from bridgy.tools import pdf_loader
    print('✅ Successfully imported pdf_loader via bridgy')
    success = True
except ImportError as e:
    print(f'❌ Import error via bridgy: {e}')

try:
    from tools import pdf_loader
    print('✅ Successfully imported pdf_loader via direct tools import')
    success = True
except ImportError as e:
    print(f'❌ Import error via direct tools: {e}')

if success:
    print("Import verification successful")
    sys.exit(0)
else:
    print("Import verification failed")
    sys.exit(1)
