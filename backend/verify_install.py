import importlib

packages = [
    'django',
    'chromadb',
    'sentence_transformers',
    'rest_framework',
    'corsheaders',
    'PyPDF2',
    'docx',
    'numpy',
    'requests',
]

print("=== Verifying installed packages ===")
for pkg in packages:
    try:
        mod = importlib.import_module(pkg)
        version = getattr(mod, '__version__', 'installed')
        print(f"  ✅ {pkg} ({version})")
    except Exception as e:
        print(f"  ❌ {pkg} - FAILED: {e}")

print("\n=== Import check complete ===")