#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Test script to check admin_gui loading"""

import sys
import traceback

try:
    print("1. Importing modules...")
    import json
    import re
    import os
    from pathlib import Path
    import tkinter as tk
    from tkinter import ttk, messagebox
    print("   OK")
    
    print("2. Importing PIL...")
    from PIL import Image, ImageTk
    print("   OK")
    
    print("3. Loading projects.html...")
    with open('projects.html', 'r', encoding='utf-8') as f:
        content = f.read()
    print("   OK")
    
    print("4. Extracting JSON...")
    import re
    match = re.search(r'<script type="application/json" id="projectsData">\s*(\[[\s\S]*?\])\s*</script>', content)
    if match:
        data = json.loads(match.group(1))
        print(f"   OK - {len(data)} projects found")
    else:
        print("   FAILED - No JSON found")
    
    print("5. Importing admin_gui...")
    import admin_gui
    print("   OK")
    
    print("\nAll checks passed!")
    
except Exception as e:
    print(f"\nERROR: {e}")
    traceback.print_exc()

input("\nPress Enter to exit...")
