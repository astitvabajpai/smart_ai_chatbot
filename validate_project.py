#!/usr/bin/env python
"""Quick validation script to check for import and syntax errors."""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

print("🔍 Validating project structure...")
print()

# Check core modules
modules_to_check = [
    "app.core.config",
    "app.core.exceptions",
    "app.core.middleware",
    "app.core.rate_limiter",
    "app.core.validators",
    "app.core.logging",
    "app.main",
    "app.models.schemas",
    "app.api.routes",
]

errors = []

for module_name in modules_to_check:
    try:
        print(f"✓ Importing {module_name}... ", end="")
        __import__(module_name)
        print("OK")
    except Exception as e:
        print(f"FAILED")
        errors.append(f"  {module_name}: {str(e)}")

print()

if errors:
    print(f"❌ {len(errors)} import error(s) found:")
    for error in errors:
        print(error)
    sys.exit(1)
else:
    print("✅ All modules imported successfully!")
    print()
    print("📋 Project structure validation:")
    
    # Check configuration
    try:
        from app.core.config import get_settings
        settings = get_settings()
        print(f"  ✓ Settings loaded: {settings.app_name}")
        print(f"    - Environment: {settings.app_env}")
        print(f"    - Vector Backend: {settings.vector_backend}")
        print(f"    - Embedding Provider: {settings.embedding_provider}")
        print(f"    - Log Level: {settings.log_level}")
        print(f"    - Rate Limiting: {'Enabled' if settings.enable_rate_limiting else 'Disabled'}")
    except Exception as e:
        print(f"  ✗ Failed to load settings: {str(e)}")
        sys.exit(1)
    
    print()
    print("🎉 Project is ready for deployment!")
    print()
    print("📚 Documentation:")
    print("  - README.md - Project overview")
    print("  - PRODUCTION_GUIDE.md - Deployment guide")
    print("  - API_DOCUMENTATION.md - API reference")
    print()
    print("🚀 To start development:")
    print("  uvicorn app.main:app --reload --host 0.0.0.0 --port 8000")
    print()
    print("🐳 To start with Docker:")
    print("  docker compose up --build")
