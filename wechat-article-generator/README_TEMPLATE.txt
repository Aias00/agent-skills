# 微信公众号文章生成包

**文章**: {{title}}
**主题**: {{topic}}
**生成时间**: {{date}}
**目录**: {{slug}}

## 文件说明

1. article.md - Markdown 源文件
2. article-wechat.html - 微信兼容 HTML 文件（已转为 `<p>` + inline style）
3. images/ - 配图目录（封面与正文图片）

## 推荐发布方式

### 方式 A（推荐）: 使用第三方微信排版工具中转

1. 打开微信排版工具（如秀米、135 编辑器等）
2. 导入或粘贴 `article-wechat.html` 的渲染内容
3. 检查标题、段落、代码块与表格样式
4. 同步到公众号编辑器后上传 `images/` 目录中的图片
5. 预览并发布

### 方式 B: 直接使用 Markdown

1. 打开微信公众号后台: https://mp.weixin.qq.com
2. 进入「内容管理」→「新建图文」
3. 复制 `article.md` 的正文内容
4. 在编辑器中调整样式并插入图片
5. 预览并发布

## 二次修改

修改 `article.md` 后，可重新生成 HTML：

```bash
python3 scripts/markdown-to-wechat.py article.md --out article-wechat.html
```

## 说明

- 该包默认不自动发布到公众号后台。
- 如需多平台分发，建议保留 Markdown 作为主源文件。

---

Generated with WeChat Article Generator Skill
