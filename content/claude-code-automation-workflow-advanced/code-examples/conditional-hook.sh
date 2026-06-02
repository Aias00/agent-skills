#!/bin/bash
# conditional-hook.sh
# 在脚本内部判断当前目录或文件类型
# 用于 Stop 钩子等不支持 matcher 的场景

# 获取当前工作目录
CWD="${CLAUDE_PROJECT_DIR:-$(pwd)}"

# 判断是否在文章工作区
if [[ "$CWD" == *"articles/workspaces"* ]]; then
  echo "📝 在文章工作区，执行文章相关操作..."

  # 检查是否有变更
  if git diff --quiet 2>/dev/null; then
    echo "没有变更，跳过提交"
    exit 0
  fi

  # 自动提交草稿
  git add .
  git commit -m "auto: draft save at $(date +%Y%m%d-%H%M)" 2>/dev/null || true
  echo "✅ 草稿已保存"
fi

# 判断文章类型并执行不同操作
if [ -f "article.md" ]; then
  TYPE=$(grep -E "^type:" article.md | head -1 | cut -d: -f2 | tr -d ' ')

  case "$TYPE" in
    tech)
      echo "技术文章，运行完整检查..."
      # 可以在这里调用 make review
      ;;
    repost)
      echo "转载文章，跳过审阅..."
      ;;
    draft)
      echo "草稿，仅保存..."
      ;;
  esac
fi
