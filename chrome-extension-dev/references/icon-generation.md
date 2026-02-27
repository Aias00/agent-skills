# Chrome Extension Icon Generation Guide

Complete guide to generating professional icons for Chrome extensions using AI image generation.

## Why Custom Icons Matter

❌ **Don't use placeholder icons** - They look unprofessional and reduce user trust
✅ **Generate custom icons** - Reflect your extension's functionality and build brand recognition

## Icon Requirements

Chrome requires icons in specific sizes:

- **16x16** - Toolbar icon, favicon
- **32x32** - Windows computers often use this
- **48x48** - Extension management page
- **128x128** - Chrome Web Store, installation dialog

**Best practice**: Generate a high-resolution icon (512x512 or larger) and resize down.

## AI-Powered Icon Generation

### Using FLUX (Recommended)

```bash
# Install CLI
curl -fsSL https://cli.inference.sh | sh && infsh login

# Generate icon
infsh app run falai/flux-dev-lora --input '{
  "prompt": "YOUR_PROMPT_HERE"
}'
```

### Using Gemini 3 Pro

```bash
infsh app run google/gemini-3-pro-image-preview --input '{
  "prompt": "YOUR_PROMPT_HERE"
}'
```

### Using Seedream 4.5 (Highest Quality)

```bash
infsh app run bytedance/seedream-4-5 --input '{
  "prompt": "YOUR_PROMPT_HERE"
}'
```

## Prompt Templates by Extension Type

### 🌙 Dark Mode / Theme Extensions

**Prompt**:
```
simple icon of a crescent moon on dark background, minimalist design, clean vector style, app icon, professional, high contrast, centered composition, white moon on dark blue background, no text
```

**Alternative**:
```
icon showing light bulb half dark half light, symbolizing dark mode toggle, clean flat design, app icon style, centered, minimalist
```

### 📝 Note Taking / Text Extensions

**Prompt**:
```
simple icon of a pencil or pen, minimalist design, clean vector style, app icon, professional, centered composition, blue or teal color scheme, flat design, no text
```

**Alternative**:
```
icon of a notepad with pencil, clean modern design, app icon style, minimal details, centered, soft colors
```

### 🎵 Music / Audio Extensions

**Prompt**:
```
simple icon of headphones or musical note, minimalist design, clean vector style, app icon, professional, centered composition, vibrant colors, flat design, no text
```

**Alternative**:
```
icon of sound wave bars, modern design, app icon style, minimal, centered, gradient colors from purple to blue
```

### 📊 Productivity / Task Extensions

**Prompt**:
```
simple icon of a checklist or clipboard, minimalist design, clean vector style, app icon, professional, centered composition, green or blue color scheme, flat design, no text
```

**Alternative**:
```
icon showing gears or clock symbolizing productivity, clean modern design, app icon style, minimal details, centered
```

### 🔒 Privacy / Security Extensions

**Prompt**:
```
simple icon of a shield or lock, minimalist design, clean vector style, app icon, professional, centered composition, blue or green color scheme, flat design, no text
```

**Alternative**:
```
icon of an eye with a line through it (privacy symbol), clean modern design, app icon style, minimal, centered, dark blue
```

### 💰 Finance / Shopping Extensions

**Prompt**:
```
simple icon of a dollar sign or shopping cart, minimalist design, clean vector style, app icon, professional, centered composition, green color scheme, flat design, no text
```

**Alternative**:
```
icon showing coins or piggy bank, clean modern design, app icon style, minimal details, centered, gold or green
```

### 🌐 Translation / Language Extensions

**Prompt**:
```
simple icon of a globe or letter A and Chinese character, minimalist design, clean vector style, app icon, professional, centered composition, blue color scheme, flat design, no text
```

**Alternative**:
```
icon showing translation symbol or language flags, clean modern design, app icon style, minimal, centered
```

### 📸 Screenshot / Image Extensions

**Prompt**:
```
simple icon of a camera or photo frame, minimalist design, clean vector style, app icon, professional, centered composition, purple or blue color scheme, flat design, no text
```

**Alternative**:
```
icon of scissors representing screenshot crop tool, clean modern design, app icon style, minimal details, centered
```

### 🔍 Search / Finder Extensions

**Prompt**:
```
simple icon of a magnifying glass, minimalist design, clean vector style, app icon, professional, centered composition, blue or orange color scheme, flat design, no text
```

**Alternative**:
```
icon showing search symbol with light beam, clean modern design, app icon style, minimal, centered
```

### 📧 Email / Communication Extensions

**Prompt**:
```
simple icon of an envelope or letter, minimalist design, clean vector style, app icon, professional, centered composition, blue color scheme, flat design, no text
```

**Alternative**:
```
icon showing chat bubble or mail symbol, clean modern design, app icon style, minimal details, centered
```

### ⏱️ Timer / Alarm Extensions

**Prompt**:
```
simple icon of a clock or stopwatch, minimalist design, clean vector style, app icon, professional, centered composition, red or blue color scheme, flat design, no text
```

**Alternative**:
```
icon showing hourglass or timer symbol, clean modern design, app icon style, minimal details, centered
```

### 🎨 Color / Design Extensions

**Prompt**:
```
simple icon of a color palette or paintbrush, minimalist design, clean vector style, app icon, professional, centered composition, rainbow colors, flat design, no text
```

**Alternative**:
```
icon showing dropper or color wheel, clean modern design, app icon style, minimal details, centered
```

### 📚 Learning / Education Extensions

**Prompt**:
```
simple icon of a book or graduation cap, minimalist design, clean vector style, app icon, professional, centered composition, blue or green color scheme, flat design, no text
```

**Alternative**:
```
icon showing light bulb or brain symbol, clean modern design, app icon style, minimal details, centered
```

### 🛠️ Developer Tools Extensions

**Prompt**:
```
simple icon of a code bracket or terminal, minimalist design, clean vector style, app icon, professional, centered composition, dark background with bright accent color, flat design, no text
```

**Alternative**:
```
icon showing gear or wrench representing tools, clean modern design, app icon style, minimal details, centered
```

## Design Principles

### 1. Simplicity

✅ **Good**: Single recognizable symbol
❌ **Bad**: Complex scene with multiple elements

**Example**:
- ✅ Simple magnifying glass
- ❌ Person using magnifying glass on a desk with coffee

### 2. Readability at Small Sizes

Icons must be recognizable at 16x16 pixels.

✅ **Good**: Bold shapes, high contrast
❌ **Bad**: Thin lines, subtle details

### 3. Centered Composition

Keep the main element centered with adequate padding.

### 4. Consistent Color Scheme

Use 1-3 colors maximum. Avoid gradients in small icons.

**Recommended color palettes**:
- Blue/White: Trust, professional
- Green/White: Success, money
- Purple/White: Creative, premium
- Red/White: Urgent, important
- Orange/White: Energy, friendly

### 5. No Text

Icons should convey meaning without text. Users speak many languages.

## Icon Generation Workflow

### Step 1: Define Your Extension's Core Concept

Ask yourself:
- What is the primary function?
- What symbol best represents it?
- What emotion or feeling should it convey?

### Step 2: Choose a Prompt Template

Select from the templates above or create your own.

### Step 3: Generate High-Resolution Icon

```bash
# Generate 512x512 or larger
infsh app run falai/flux-dev-lora --input '{
  "prompt": "YOUR_PROMPT_HERE"
}'
```

### Step 4: Download and Resize

Use Python to resize to required sizes:

```python
from PIL import Image

# Load high-res icon
img = Image.open('icon_512.png')

# Generate all sizes
sizes = [16, 32, 48, 128]
for size in sizes:
    resized = img.resize((size, size), Image.LANCZOS)
    resized.save(f'icon{size}.png')
    print(f'✅ Created icon{size}.png')
```

### Step 5: Optimize (Optional)

Compress PNG files to reduce extension size:

```bash
# Install pngquant
brew install pngquant

# Optimize all icons
pngquant --quality=65-80 --ext .png --force icon*.png
```

## Complete Example: Dark Mode Extension

### 1. Generate Icon

```bash
infsh app run falai/flux-dev-lora --input '{
  "prompt": "simple icon of a crescent moon on dark background, minimalist design, clean vector style, app icon, professional, high contrast, centered composition, white moon on dark blue background, no text"
}'
```

### 2. Download Result

Save the generated image as `icon_512.png`

### 3. Resize

```python
from PIL import Image

img = Image.open('icon_512.png')

for size in [16, 32, 48, 128]:
    resized = img.resize((size, size), Image.LANCZOS)
    resized.save(f'icons/icon{size}.png')
```

### 4. Update manifest.json

```json
{
  "icons": {
    "16": "icons/icon16.png",
    "32": "icons/icon32.png",
    "48": "icons/icon48.png",
    "128": "icons/icon128.png"
  },
  "action": {
    "default_icon": {
      "16": "icons/icon16.png",
      "32": "icons/icon32.png",
      "48": "icons/icon48.png"
    }
  }
}
```

## Tips for Better Icons

### 1. Iterate and Refine

Generate multiple versions and choose the best:

```bash
# Generate 4 variations
for i in {1..4}; do
  infsh app run falai/flux-dev-lora --input '{
    "prompt": "YOUR_PROMPT_HERE"
  }'
done
```

### 2. Test at Actual Size

View your icons at 16x16 pixels to ensure they're readable:

```python
from PIL import Image

img = Image.open('icon16.png')
img.show()  # Open at actual size
```

### 3. Get Feedback

Share icons with others before finalizing.

### 4. Consider Dark Mode

Test how your icon looks on both light and dark backgrounds.

### 5. Align with Brand

If your extension has a website, match the color scheme.

## Common Mistakes to Avoid

❌ **Too detailed**: Details get lost at small sizes
❌ **Multiple elements**: Confusing and unclear
❌ **Thin lines**: Disappear at 16x16
❌ **Text in icon**: Not translatable
❌ **Gradient backgrounds**: Look muddy at small sizes
❌ **Off-center**: Looks unprofessional

## Alternative: Icon Generators

If you don't want to use AI, consider these alternatives:

1. **Canva** - Icon templates
2. **Figma** - Design from scratch
3. **Font Awesome** - Use icons as base
4. **Material Icons** - Google's icon library
5. **Icon8** - Pre-made icons

However, AI-generated icons are:
- ✅ Unique to your extension
- ✅ Perfectly match your concept
- ✅ Professional quality
- ✅ Quick to generate

## Resources

- [AI Image Generation Skill](https://github.com/inference-sh/skills) - For generating icons
- [Chrome Icon Guidelines](https://developer.chrome.com/docs/webstore/images/) - Official requirements
- [Material Design Icons](https://fonts.google.com/icons) - Reference for icon styles

## Summary

1. **Never use placeholder icons** - Generate custom icons for your extension
2. **Use AI image generation** - Quick, professional, unique
3. **Follow design principles** - Simple, centered, high contrast
4. **Generate all required sizes** - 16, 32, 48, 128
5. **Test at actual size** - Ensure readability at 16x16

Professional icons increase user trust and make your extension stand out in the Chrome Web Store! 🎨
