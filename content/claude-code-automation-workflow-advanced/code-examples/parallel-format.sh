#!/bin/bash
# parallel-format.sh
# 用法：./parallel-format.sh articles/workspaces/my-article/my-article.md
# 功能：并行生成多个平台的 HTML

ARTICLE=$1
BASENAME=$(basename "$ARTICLE" .md)
DIR=$(dirname "$ARTICLE")

if [ -z "$ARTICLE" ]; then
  echo "用法: $0 <article.md>"
  exit 1
fi

# 并行执行三个格式化任务
wechat-article-formatter/.venv/bin/python \
  wechat-article-formatter/scripts/markdown_to_html.py \
  --input "$ARTICLE" --theme mist-blue \
  --output "$DIR/$BASENAME-wechat.html" &

wechat-article-formatter/.venv/bin/python \
  wechat-article-formatter/scripts/markdown_to_html.py \
  --input "$ARTICLE" --theme tech-blue \
  --output "$DIR/$BASENAME-toutiao.html" &

wechat-article-formatter/.venv/bin/python \
  wechat-article-formatter/scripts/markdown_to_html.py \
  --input "$ARTICLE" --theme forest \
  --output "$DIR/$BASENAME-blog.html" &

# 等待所有任务完成
wait

echo "✅ 三个平台的 HTML 已生成"
echo "   - $DIR/$BASENAME-wechat.html"
echo "   - $DIR/$BASENAME-toutiao.html"
echo "   - $DIR/$BASENAME-blog.html"
