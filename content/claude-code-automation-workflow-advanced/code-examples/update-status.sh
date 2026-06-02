#!/bin/bash
# update-status.sh
# 用法：./update-status.sh article.md ready
# 功能：更新文章 frontmatter 中的状态字段

FILE=$1
NEW_STATUS=$2

if [ -z "$FILE" ] || [ -z "$NEW_STATUS" ]; then
  echo "用法: $0 <article.md> <status>"
  echo "状态: draft | reviewing | ready | published"
  exit 1
fi

if [ ! -f "$FILE" ]; then
  echo "错误: 文件不存在 $FILE"
  exit 1
fi

# 备份原文件
cp "$FILE" "${FILE}.bak"

# 更新 status 字段
sed -i "s/^status:.*/status: $NEW_STATUS/" "$FILE"

# 更新 updated 时间戳
sed -i "s/^updated:.*/updated: $(date +%Y-%m-%d)/" "$FILE"

# 如果状态是 published，添加发布时间
if [ "$NEW_STATUS" = "published" ]; then
  sed -i "s/^published_at:.*/published_at: $(date +%Y-%m-%d)/" "$FILE"
fi

# 清理备份
rm -f "${FILE}.bak"

echo "✅ 状态已更新为: $NEW_STATUS"
