#!/usr/bin/env python3
import sys
import importlib
import os

def verify_import(module_name):
    try:
        module = importlib.import_module(module_name)
        if hasattr(module, "__version__"):
            print(f"✅ Successfully imported {module_name} (version: {module.__version__})")
        else:
            print(f"✅ Successfully imported {module_name}")
        return True
    except ImportError as e:
        print(f"❌ Import error for {module_name}: {e}")
        return False

# Add all import paths
sys.path.extend(["/app", "/app/bridgy-main", "/app/bridgy", "/tmp"])

# Check critical modules
critical_modules = [
    "numpy", "scipy", "sklearn", "pypdf", "motor", "pymongo",
    "sentence_transformers", "faiss"
]

for module in critical_modules:
    verify_import(module)

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
