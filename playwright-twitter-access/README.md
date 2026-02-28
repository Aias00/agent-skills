# OpenClaw Browser Twitter Access

使用 OpenClaw 的 browser 工具（基于 CDP - Chrome DevTools Protocol）访问和抓取 Twitter (X.com) 内容的专业技能。

---

## 📝 技术说明

### 核心技术：CDP (Chrome DevTools Protocol)

OpenClaw browser 工具通过 **CDP 协议** 控制浏览器：

```
调用层级：
┌─────────────────────────────────────┐
│ 1. 用户调用 → OpenClaw browser 工具  │
├─────────────────────────────────────┤
│ 2. OpenClaw browser → CDP 协议      │ ← 控制层
├─────────────────────────────────────┤
│ 3. Chrome 浏览器 → 访问 x.com        │ ← 执行层
└─────────────────────────────────────┘
```

**CDP 配置**:
- CDP 端口: `18800`
- CDP URL: `http://127.0.0.1:18800`
- WebSocket 连接: 持续通信

---

## 📋 快速开始

### 1. 前置条件

确保 OpenClaw browser 工具已启用：
```bash
browser action=status
```

**预期返回**:
```json
{
  "enabled": true,
  "cdpReady": true,
  "cdpPort": 18800
}
```

### 2. 启动浏览器
```bash
browser action=start profile=openclaw
```

### 3. 打开 Twitter 页面
```bash
# 用户主页
browser action=open targetUrl="https://x.com/elonmusk"

# 单条推文
browser action=open targetUrl="https://x.com/elonmusk/status/2027644868881957020"
```

### 4. 等待加载并获取数据
```bash
sleep 5
browser action=snapshot depth=5 refs=role
browser action=screenshot type="png"
```

---

## 🚀 核心功能

### ✅ 支持的功能

- **用户信息提取**: 用户名、验证状态、帖子数、粉丝数
- **推文内容获取**: 完整推文文本、Quote 引用
- **互动数据提取**: Replies、Reposts、Likes、Views、Bookmarks
- **回复列表抓取**: 完整的回复线程
- **图片检测**: 识别和提取推文中的图片链接
- **页面截图**: 保存推文页面截图
- **搜索功能**: 搜索推特话题和关键词

### 🎯 适用场景

- 需要获取推文回复（Jina API 不支持）
- 需要访问登录内容（Chrome Extension Relay）
- 需要图片和多媒体内容
- 需要页面截图和可视化
- 需要研究推文互动数据

---

## 📖 使用示例

### 示例 1: 抓取单条推文

```bash
# 打开推文
browser action=open targetUrl="https://x.com/elonmusk/status/2027644868881957020"

# 等待加载
sleep 5

# 获取快照（包含用户、内容、互动数据、回复）
browser action=snapshot depth=5 refs=role

# 截图
browser action=screenshot type="png"
```

### 示例 2: 批量抓取用户主页

```bash
# 启动浏览器
browser action=start profile=openclaw

# 批量打开
for user in elonmusk billgates nasa; do
  browser action=open targetUrl="https://x.com/$user"
  sleep 5
  browser action=snapshot depth=5 refs=role
  browser action=screenshot type="png"
done
```

### 示例 3: 使用便捷脚本

```bash
# 抓取用户主页
~/.openclaw/workspace/skills/playwright-twitter-access/fetch_twitter.sh user elonmusk

# 抓取单条推文
fetch_twitter.sh tweet https://x.com/elonmusk/status/2027644868881957020

# 搜索推特
fetch_twitter.sh search "AI technology"
```

---

## 📊 访问工具对比

| 功能 | Jina API | OpenClaw Browser (CDP) | Chrome Relay |
|------|----------|----------------------|--------------|
| 推文内容 | ✅ 极快 | ✅ 完整 | ✅ 完整 |
| 回复列表 | ❌ 不支持 | ✅ 完整 | ✅ 完整 |
| 登录内容 | ❌ 不支持 | ⚠️ 新实例 | ✅ 已登录 |
| 图片/视频 | ❌ 不支持 | ✅ 截图/链接 | ✅ 截图/链接 |
| 速度 | ⚡ 1-2秒 | 🐢 5-10秒 | 🐢 5-10秒 |
| 成本 | 免费但有限制 | 完全免费 | 完全免费 |
| 技术 | HTTP API | CDP 协议 | CDP + 扩展 |
| 推荐场景 | 公开推文 | 回复/交互 | 私人内容 |

### 选择建议

- **公开推文快速抓取**: 使用 Jina API（twitter_fetcher.py）
- **回复/交互复杂场景**: 使用 OpenClaw Browser (CDP, 本 skill)
- **需要登录/私人内容**: 使用 Chrome Extension Relay

---

## 🔧 核心命令

### Browser 工具命令

| 命令 | 说明 | 参数 |
|------|------|------|
| `browser action=start` | 启动浏览器 | `profile=openclaw/chrome` |
| `browser action=open` | 打开页面 | `targetUrl="..."` |
| `browser action=snapshot` | 获取快照 | `depth=3-5, refs=role/aria` |
| `browser action=screenshot` | 截取页面 | `type=png/jpeg` |
| `browser action=act` | 点击/交互 | `kind=click/type/press` |
| `browser action=status` | 查看状态 | - |

### 高级技巧

#### 滚动加载更多内容
```bash
browser action=act request='{"kind":"press","key":"End"}'
sleep 3
browser action=snapshot depth=5 refs=role
```

#### 使用 Chrome Relay（登录状态）
```bash
# 前提: Chrome 已登录 X.com，Extension Relay 已连接
browser action=open targetUrl="https://x.com/..." profile=chrome
```

---

## 🗂️ 文件结构

```
skills/playwright-twitter-access/
├── SKILL.md              # 完整技能文档
├── fetch_twitter.sh      # 便捷抓取脚本
├── README.md            # 本文件（快速指南）
└── outputs/             # 输出文件目录
    ├── elonmusk_snapshot.json
    ├── 2027644868881957020_tweet_snapshot.json
    └── ...              # 其他输出的 JSON/文件
```

---

## 📝 数据结构

### Snapshot 返回结构

```json
{
  "document": {
    "banner": { ... },
    "main": {
      "heading": "Elon Musk Verified account",
      "heading": "Post",
      "region": "Conversation",
      "article": [ ... ]  // 推文和回复
    }
  }
}
```

### 推文数据元素

```json
{
  "article": {
    "link": "Elon Musk Verified account",
    "link": "@elonmusk",
    "text": "推文内容...",
    "link": "7 hours ago",
    "group": {
      "button": "3560 Replies",
      "button": "8964 reposts",
      "button": "71087 Likes",
      "link": "35753772 views"
    }
  }
}
```

---

## 🎓 学习资源

### 官方文档
- OpenClaw Browser 工具文档
- Twitter (X.com) 官网
- Playwright 官方文档

### 相关 Skill
- `twitter_fetcher` - Jina API 抓取推文
- `agent-browser` - 浏览器自动化 CLI
- `browser` - OpenClaw 内置 browser 工具

### 集成示例
- Twitter Pipeline - `twitter_pipeline/twitter_fetcher.py`
- 示例脚本 - `fetch_twitter.sh`

---

## ⚠️ 注意事项

### 限制

1. **回复加载**: 需要滚动，可能多次操作
2. **批量性能**: 不适合大规模批量抓取（使用 Jina API）
3. **速率限制**: Twitter 可能限制自动化访问
4. **网络延迟**: 每条推文需要 5-10 秒加载时间

### 最佳实践

1. **混合使用**: Jina API 抓取推文 + OpenClaw Browser (CDP) 抓取回复
2. **缓存数据**: 避免重复抓取相同内容
3. **延迟优化**: 根据网络调整 `sleep` 时间
4. **登录访问**: 私人内容使用 Chrome Extension Relay

---

## 🔗 常见问题 (FAQ)

### Q: 为什么使用浏览器而不是 API?
A: Twitter API 有严格的限制和成本，而浏览器访问更灵活、免费。

### Q: 会触发 Cloudflare 验证吗?
A: 通常不会。如遇验证，使用 Chrome Extension Relay 或增加延迟。

### Q: 如何批量抓取?
A: 不推荐。大规模批量抓取请使用 Jina API（Twitter Pipeline）。

### Q: 可以抓取私人推文吗?
A: 可以，使用 Chrome Extension Relay 保持登录状态。

---

## 📈 性能指标

### 操作时间

- **打开页面**: 2-3 秒
- **等待加载**: 3-5 秒
- **获取快照**: 1-2 秒
- **截图保存**: 1-2 秒
- **总计**: 7-12 秒/推文

### 单条推文完整流程

```bash
browser action=open ...      # 2-3s
sleep 5                      # 5s
browser action=snapshot ...  # 1-2s
browser action=screenshot    # 1-2s
                            # 总计: ~9-12s
```

---

## 🚀 未来扩展

### 计划功能

- [ ] 自动滚动加载完整回复线程
- [ ] 图片自动下载和保存
- [ ] 数据模板化输出（JSON/CSV）
- [ ] 批量抓取包装脚本
- [ ] Web UI 界面

### 贡献建议

需要新功能或发现 bug？欢迎反馈！

---

## 📦 技术栈

- **OpenClaw Browser**: 基于 CDP (Chrome DevTools Protocol) 的浏览器控制工具
- **CDP Protocol**: Chrome DevTools 协议，用于远程控制浏览器
- **Chrome**: 真实浏览器实例（自动启动）
- **playwright-core**: 辅助功能（OpenClaw 依赖项）
- **Jina API**: 对比工具（快速抓取公开推文）

---

## 📄 许可证

本技能是 OpenClaw 项目的一部分，遵循项目许可协议。

---

**技能版本**: 1.0.0
**创建时间**: 2026-02-28
**维护者**: Clawd (AI Assistant)
**状态**: ✅ 生产可用