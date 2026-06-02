---
name: article-process
description: 根据文章类型执行不同处理流程
triggers:
  - "处理文章"
  - "文章流程"
---

## 执行逻辑

1. 读取文章 frontmatter 中的 `type` 字段
2. 根据类型执行不同流程：

**type: tech（技术文章）**
1. 运行技术审阅
2. 运行禁用词检查
3. 格式化为 HTML
4. 生成封面图
5. 询问是否发布

**type: repost（转载文章）**
1. 格式化为 HTML
2. 生成封面图
3. 询问是否发布

**type: draft（草稿）**
1. 仅保存备份
2. 提示「草稿已保存」

3. 更新 frontmatter 中的 `status` 字段
