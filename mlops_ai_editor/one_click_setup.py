#!/usr/bin/env python3
"""
One-Click Setup for MLOps AI Editor
Downloads everything and sets up automatically.
"""

import urllib.request
import zipfile
import os
import sys
import subprocess
import shutil
from pathlib import Path

        
        # Install dependencies
        print("\n📦 Installing dependencies...")
        subprocess.run([sys.executable, "-m", "pip", "install", "-r", "requirements.txt"])
        
        print("\n🎉 Setup Complete!")
        print("\n🚀 To start the editor:")
        print("   cd mlops_ai_editor")
        print("   python main.py")
        
        # Ask to launch
        response = input("\n🎯 Launch editor now? (y/n): ")
        if response.lower() == 'y':
            os.chdir("mlops_ai_editor")
            subprocess.run([sys.executable, "main.py"])
        
    except Exception as e:
        print(f"❌ Error during setup: {e}")
        return False
    
    return True

if __name__ == "__main__":
    download_and_setup()
