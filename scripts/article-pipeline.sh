#!/bin/bash
set -euo pipefail

REPO="$(cd "$(dirname "$0")/.." && pwd)"
INPUT=""
THEME="ai-tech"
COVER=false
PUBLISH=false
SKIP_REVIEW=false

while [[ $# -gt 0 ]]; do
  case "$1" in
    --input) INPUT="$2"; shift 2 ;;
    --theme) THEME="$2"; shift 2 ;;
    --cover) COVER=true; shift ;;
    --publish) PUBLISH=true; shift ;;
    --skip-review) SKIP_REVIEW=true; shift ;;
    *) echo "Unknown arg: $1"; exit 1 ;;
  esac
done

if [[ -z "$INPUT" ]]; then
  echo "Usage: article-pipeline.sh --input <article.md> [--theme ai-tech] [--cover] [--publish] [--skip-review]"
  exit 1
fi

INPUT="$(cd "$(dirname "$INPUT")" && pwd)/$(basename "$INPUT")"
HTML="${INPUT%.md}.wechat-publisher.html"
PYTHON="$REPO/wechat-article-formatter/.venv/bin/python"

echo "=== Article Pipeline ==="
echo "Input:  $INPUT"
echo "Theme:  $THEME"
echo "Cover:  $COVER"
echo "Publish: $PUBLISH"
echo ""

# Step 1: Banned pattern check
if [[ "$SKIP_REVIEW" == "false" ]]; then
  echo "[1/5] Banned scaffolding check..."
  python3 "$REPO/technical-article-review/scripts/check_banned_scaffolding.py" --input "$INPUT"
  echo "  [OK]"
fi

# Step 2: Format MD → HTML with theme
echo "[2/5] Format MD → HTML (theme: $THEME)..."
"$PYTHON" "$REPO/wechat-article-formatter/scripts/markdown_to_html.py" \
  --input "$INPUT" \
  --output "$HTML" \
  --theme "$THEME"
echo "  [OK]"

# Step 3: Cover (optional)
if [[ "$COVER" == "true" ]]; then
  echo "[3/5] Generate cover..."
  python3 "$REPO/wechat-publisher/scripts/generate-cover-image.py" \
    --markdown "$INPUT" \
    --theme purple \
    --badge ""
  echo "  [OK]"
else
  echo "[3/5] Cover: skipped"
fi

# Step 4: Preflight
echo "[4/5] Preflight..."
python3 "$REPO/technical-article-preflight/scripts/run_preflight.py" \
  --markdown "$INPUT" \
  --html "$HTML" \
  --skip-banned
echo "  [OK]"

# Step 5: Publish or dry-run
if [[ "$PUBLISH" == "true" ]]; then
  echo "[5/5] Publishing to WeChat..."
  (cd "$REPO/wechat-publisher" && bun scripts/wechat-publish.ts "$HTML")
  echo "  [OK] Published"
else
  echo "[5/5] Dry-run (pass --publish to actually publish)..."
  (cd "$REPO/wechat-publisher" && bun scripts/wechat-publish.ts "$HTML" --dry-run)
  echo "  [OK] Dry-run passed"
fi

echo ""
echo "=== Pipeline complete ==="
