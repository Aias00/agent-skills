#!/usr/bin/env python3
"""
Resize extension icons to all required Chrome extension sizes.
Usage: python resize_icons.py <input_image>
"""

import sys
from PIL import Image
import os

def resize_icons(input_path):
    """Resize icon to all required Chrome extension sizes."""
    
    # Check if file exists
    if not os.path.exists(input_path):
        print(f"❌ Error: File not found: {input_path}")
        return
    
    # Load image
    try:
        img = Image.open(input_path)
        print(f"✅ Loaded image: {input_path}")
        print(f"   Original size: {img.size}")
    except Exception as e:
        print(f"❌ Error loading image: {e}")
        return
    
    # Create icons directory if it doesn't exist
    icons_dir = "icons"
    os.makedirs(icons_dir, exist_ok=True)
    
    # Required sizes for Chrome extensions
    sizes = [16, 32, 48, 128]
    
    print(f"\n🎨 Generating icons...")
    
    for size in sizes:
        # Resize using high-quality resampling
        resized = img.resize((size, size), Image.LANCZOS)
        
        # Save
        output_path = os.path.join(icons_dir, f"icon{size}.png")
        resized.save(output_path, "PNG", optimize=True)
        
        # Get file size
        file_size = os.path.getsize(output_path)
        print(f"   ✅ icon{size}.png ({file_size:,} bytes)")
    
    print(f"\n✨ All icons generated in '{icons_dir}/' directory!")
    print(f"\n📝 Add to manifest.json:")
    print(f'''
{{
  "icons": {{
    "16": "icons/icon16.png",
    "32": "icons/icon32.png",
    "48": "icons/icon48.png",
    "128": "icons/icon128.png"
  }},
  "action": {{
    "default_icon": {{
      "16": "icons/icon16.png",
      "32": "icons/icon32.png",
      "48": "icons/icon48.png"
    }}
  }}
}}
''')

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python resize_icons.py <input_image>")
        print("Example: python resize_icons.py my_icon.png")
        sys.exit(1)
    
    resize_icons(sys.argv[1])
