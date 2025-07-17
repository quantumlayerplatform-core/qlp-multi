# Quick dependencies check script
import sys
import subprocess

def install_if_missing(package):
    try:
        __import__(package)
        print(f"✅ {package} is already installed")
    except ImportError:
        print(f"📦 Installing {package}...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", package])

# Install required packages
install_if_missing("httpx")
install_if_missing("asyncio")

print("🎉 All dependencies ready!")
