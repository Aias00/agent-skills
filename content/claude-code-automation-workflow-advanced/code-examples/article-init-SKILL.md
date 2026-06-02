---
name: article-init
description: 从模板创建新文章
triggers:
  - "创建文章"
  - "新文章"
---

## 执行步骤

1. 询问用户文章主题（用于生成目录名）
2. 询问文章类型：
   - 技术文章 → 使用 technical 模板
   - 转载文章 → 使用 repost 模板
   - 随笔 → 使用 essay 模板
3. 在 articles/workspaces/ 下创建目录：`{主题slug}/`
4. 创建文件结构：
   - `{主题slug}.md`（从模板复制）
   - `imgs/` 目录
5. 初始化 Git 分支：`git checkout -b article/{主题slug}`
6. 输出：已创建文章，可以开始写作

## 模板

技术文章模板 frontmatter：

```markdown
---
title: {标题}
created: {日期}
status: draft
type: tech
---
```
