# OpenClaw Browser Twitter Access

使用 OpenClaw 的 browser 工具（基于 CDP - Chrome DevTools Protocol）访问和抓取 Twitter (X.com) 内容。

---

## 📝 技术说明

### 架构概述

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

### CDP (Chrome DevTools Protocol)

OpenClaw browser 工具的核心是 **CDP 协议**，而非直接的 Playwright 控制：

```json
{
  "enabled": true,
  "cdpPort": 18800,              // Chrome DevTools 端口
  "cdpUrl": "http://127.0.0.1:18800",  // CDP API 地址
  "cdpReady": true,               // CDP 连接状态
  "cdpHttp": true
}
```

**CDP 工作原理**:
1. OpenClaw 启动 Chrome 时开启 CDP 端口 `--remote-debugging-port=18800`
2. 通过 HTTP/JSON 协议发送 CDP 命令控制浏览器
3. 使用 WebSocket 持久连接实时通信
4. 支持完整的浏览器操作（导航、快照、截图、交互）

### Chrome 启动参数

```bash
/Applications/Google Chrome.app/Contents/MacOS/Google Chrome \
  --remote-debugging-port=18800 \
  --user-data-dir=/Users/aias/.openclaw/browser/openclaw/user-data \
  --disable-blink-features=AutomationControlled \
  --lang=zh-CN
```

**关键参数**:
- `--remote-debugging-port=18800`: 开启 CDP 端口
- `--user-data-dir`: 用户数据目录（保持登录状态）
- `--disable-blink-features=AutomationControlled`: 禁用自动化检测

### 与 Playwright 的关系

OpenClaw 安装了 `playwright-core` 依赖，但主要用于：
- 辅助功能（如 WebSocket 连接管理）
- 不是主要的浏览器控制机制
- 主要控制通过 CDP 协议实现

**重要区分**:
- ❌ **不是**直接使用 `playwright launch()`
- ✅ **是**通过 CDP 远程控制已启动的 Chrome

---

## 适用场景

使用此技能的典型场景：
- 🔍 **提取推文内容**和完整性（支持回复、图片等）
- 📸 **截取推文页面截图**
- 💬 **获取推文回复列表**（Jina API 无法做到）
- 🎭 **访问需要登录的内容**（通过 Chrome Extension Relay）
- 🧪 **测试 Twitter API 限制**和自动化工具
- 📊 **研究推文互动数据**（Views, Reposts, Likes）

---

## 前置条件

### 1. OpenClaw Browser 工具

确保 `browser` 工具已启用且可用：
```bash
browser action=status
```

**预期返回**:
```json
{
  "enabled": true,
  "running": false/true,
  "cdpReady": true,
  "cdpPort": 18800,
  "cdpUrl": "http://127.0.0.1:18800",
  "profile": "openclaw"
}
```

### 2. Chrome 浏览器

OpenClaw 使用系统的 Chrome 浏览器：
- **macOS**: `/Applications/Google Chrome.app/Contents/MacOS/Google Chrome`
- **Linux**: `/usr/bin/google-chrome` 或类似路径
- **Windows**: `C:\Program Files\Google\Chrome\Application\chrome.exe`

检查 Chrome 是否可用：
```bash
# macOS
/Applications/Google\ Chrome.app/Contents/MacOS/Google\ Chrome --version

# Linux
google-chrome --version

# Windows
chrome.exe --version
```

### 3. OpenClaw Profile

**openclaw profile**（推荐）:
- 隔离的浏览器实例
- 独立的用户数据目录
- 不影响你的个人浏览器

```bash
browser action=start profile=openclaw
```

**chrome profile**（可选）:
- 连接到已打开的 Chrome 标签页
- 需要安装 OpenClaw Browser Relay 扩展
- 可以访问已登录的内容

```bash
browser action=open targetUrl="..." profile=chrome
```

### 4. CDP 端口可用性

确保 CDP 端口 `18800` 没有被占用：
```bash
# 检查端口占用
lsof -i :18800

# 如果被占用，OpenClaw 会自动重启浏览器
```

---

## 基础操作

### 1. 启动浏览器

```bash
browser action=start profile=openclaw
```

**返回示例**:
```json
{
  "running": true,
  "pid": 52376,
  "profile": "openclaw",
  "cdpUrl": "http://127.0.0.1:18800",
  "headless": false
}
```

### 2. 打开 Twitter 页面

#### 打开用户主页
```bash
browser action=open targetUrl="https://x.com/elonmusk"
```

#### 打开单条推文
```bash
browser action=open targetUrl="https://x.com/elonmusk/status/2027644868881957020"
```

#### 打开搜索结果
```bash
browser action=open targetUrl="https://x.com/search?q=AI&src=typed_query"
```

### 3. 等待页面加载

Twitter 页面是动态加载的，需要等待：

```bash
# 使用 sleep 命令（推荐 3-5 秒）
sleep 5
```

或使用 Playwright 的等待机制（高级技巧，见后文）。

### 4. 获取页面快照

```bash
browser action=snapshot depth=5 refs=role
```

**参数说明**:
- `depth`: 深度（1-10，推荐 3-5）
- `refs`: 定位方式（`role` 或 `aria`，推荐 `role`）

**返回内容**: 页面的 DOM 结构，包括文本内容

### 5. 截取页面截图

```bash
browser action=screenshot type="png"
```

**截图保存路径**: `/Users/aias/.openclaw/media/browser/`

---

## 核心功能

### 👤 用户信息提取

从首页快照中提取用户信息：

```python
# 典型路径结构
document → banner → main → heading "Username Verified account"
# • text: Username
# • link: @username
# • img: Verified account badge
# • text: [X]K posts
# • links: [X] Following, [X]M Followers
```

**关键数据**:
- 用户名（带验证状态）
- 帖子数量
- 关注数量
- 粉丝数量
- 加入时间

### 🐦 推文数据提取

从推文详情页快照中提取：

```python
# 推文结构
article:
  • link "Username Verified account" → 用户信息
  • link "X hours ago" → 发布时间
  • text → 推文内容
  • group "X replies, X reposts, X likes, X bookmarks, X views" → 互动数据
    • button "X Replies" → 回复数
    • button "X reposts" → 转发数
    • button "X Likes" → 点赞数
    • button "X bookmarks" → 书签数
    • link "X views" → 浏览数
```

**关键数据**:
- 作者（用户名 + 验证状态）
- 发布时间
- 推文内容
- Quote 引用（如有）
- 互动数据（Replies, Reposts, Likes, Views）

### 💬 回复列表提取

从推文详情页快照中提取回复：

```python
# 回复通常是 article 数组
main → region "Conversation" → article[1], article[2], ...

每个回复 article 包含:
  • link "Username Verified account" → 回复作者
  • link "X hours ago" → 回复时间
  • text → 回复内容
  • link "Image" → 图片（如有）
  • group → 互动数据
```

**批量提取**建议：
- 滚动页面加载更多回复（见"高级技巧"）
- 重复提取快照
- 合并所有回复数据

### 🖼️ 图片检测和提取

图片在快照中通常表现为：

```python
link "Image":
  • /url: https://x.com/username/status/123456789/photo/1
  • img "Image"
```

**操作流程**:
1. 从快照中提取图片链接
2. 使用 `web_fetch` 或直接请求下载图片
3. 保存到本地文件系统

---

## 高级技巧

### 1. 滚动页面加载更多内容

```bash
# 滚动到底部
browser action=act request='{"kind":"press","key":"End"}'

# 等待加载
sleep 3

# 获取新快照
browser action=snapshot depth=5 refs=role
```

**适用场景**:
- 加载更多推文（用户主页）
- 加载更多回复（推文详情页）

**循环加载**:
```bash
for i in {1..5}; do
  browser action=act request='{"kind":"press","key":"End"}'
  sleep 2
done
browser action=snapshot depth=5 refs=role
```

### 2. 点击元素（展开全文、查看更多）

```bash
# 点击 "Show more" 按钮
browser action=act request='{"kind":"click","ref":"Show more"}'

# 点击回复按钮
browser action=act request='{"kind":"click","ref":"Reply"}'
```

**注意事项**:
- 需要先获取快照，找到准确的 `ref`
- 元素的 `ref` 每次加载可能不同
- 等待操作完成后获取新快照

### 3. 使用 Chrome Extension Relay（登录状态）

#### 前提条件
1. 在 Chrome 浏览器中登录 X.com
2. 安装并启用 OpenClaw Browser Relay 扩展
3. 在目标标签页点击扩展图标，启用连接
4. 扩展图标变为绿色（已连接）

#### 使用方法
```bash
# 使用 chrome profile 而非 openclaw
browser action=open targetUrl="https://x.com/..." profile=chrome

# 其他操作相同
browser action=snapshot depth=5 refs=role
```

**优势**:
- 访问私人推文
- 访问需要验证的内容
- 保持登录状态
- 避免 Twitter 的登录验证

### 4. 页面等待（优化稳定性）

虽然 OpenClaw `browser` 工具不直接支持 `wait` 操作，但可以通过以下方式提高稳定性：

#### 方案 A: 增加延迟（推荐）
```bash
browser action=open targetUrl="https://x.com/..."
sleep 5  # 根据网络情况调整
browser action=snapshot
```

#### 方案 B: 检测推文元素存在
```bash
# 打开后等待
browser action=open targetUrl="https://x.com/..."
sleep 3

# 获取快照
browser action=snapshot depth=2 refs=role

# 检查是否有推文元素（手动或脚本验证）
# 然后再获取完整快照
```

---

## 与其他工具对比

| 功能 | Jina API | OpenClaw Browser (CDP) | Chrome Relay |
|------|----------|----------------------|--------------|
| **推文内容** | ✅ 极快 | ✅ 完整 | ✅ 完整 |
| **回复列表** | ❌ 不支持 | ✅ 完整 | ✅ 完整 |
| **互动数据** | ✅ 完整 | ✅ 完整 | ✅ 完整 |
| **图片** | ❌ 不支持 | ✅ 截图/链接 | ✅ 截图/链接 |
| **登录内容** | ❌ 不支持 | ⚠️ 新实例 | ✅ 已登录 |
| **批量抓取** | ✅ 高效 | ⚠️ 较慢 | ⚠️ 较慢 |
| **速度** | ⚡ 1-2秒 | 🐢 5-10秒 | 🐢 5-10秒 |
| **成本** | 免费但有限制 | 完全免费 | 完全免费 |
| **复杂度** | 简单（一行命令） | 中等（多步操作） | 中等 |
| **技术** | HTTP API | CDP 协议 | CDP + 扩展 |

### 技术栈对比

| 层级 | Jina API | OpenClaw Browser |
|------|----------|-----------------|
| **接口** | HTTP (`r.jina.ai/...`) | CLI (`browser action=...`) |
| **底层** | 服务器端抓取 | CDP 协议 + Chrome |
| **浏览器启动** | 无需 | 自动启动 |
| **用户数据** | 无（匿名） | 隔离 profile |
| **控制方式** | 基于请求 | 基于命令 |
| **websocket** | 无 | 持久连接 |

### 选择建议

#### 🥇 公开推文快速抓取 → Jina API
```bash
# 适合：大量公开推文
curl "https://r.jina.ai/http://x.com/username/status/123456789"

# 使用 Twitter Pipeline
twitter fetch https://x.com/...
```

#### 🥈 回复/交互复杂场景 → OpenClaw Browser (CDP)
```bash
# 适合：需要回复、截图、交互
browser action=start profile=openclaw
browser action=open targetUrl="https://x.com/..."
browser action=snapshot depth=5 refs=role
```

#### 🥉 登录内容访问 → Chrome Extension Relay
```bash
# 适合：私人推文、已登录状态
# 前提：Chrome 已登录，Extension Relay 已连接
browser action=open targetUrl="https://x.com/..." profile=chrome
```

#### 🪙 混合方案（最佳）
```
1. 大批公开推文 → Jina API（Twitter Pipeline）
2. 需要回复/交互 → OpenClaw Browser (CDP)
3. 需要登录内容 → Chrome Extension Relay
```

#### 🪙 混合方案（最佳）
```
1. 优先使用 Jina API 抓取推文（Twitter Pipeline 已集成）
2. 如需回复/交互，使用 Playwright (browser 工具)
3. 二者结合，发挥各自优势
```

---

## 实战示例

### 示例 1: 提取推文基本信息

```bash
# 打开推文
browser action=open targetUrl="https://x.com/elonmusk/status/2027644868881957020"

# 等待加载
sleep 5

# 获取快照
browser action=snapshot depth=5 refs=role

# 分析结果：
# ✅ 用户名: Elon Musk (Verified)
# ✅ 发布时间: 3:19 PM · Feb 28, 2026
# ✅ 推文内容: Quote Tristin Hopper...
# ✅ 互动数据: 3,561 replies, 8,967 reposts, 71,145 likes, 35.7M views
```

### 示例 2: 提取回复列表

```bash
# 打开推文
browser action=open targetUrl="https://x.com/..."

# 等待加载
sleep 5

# 获取初始快照
browser action=snapshot depth=5 refs=role

# 分析结果：看到 4 条回复：
# 1. Anas (@Anas_founder) - 6h ago
# 2. Soda Pop Comix (@SodaPopComix) - 12m ago
# 3. Popa (@popax420) - 9m ago
# 4. HollyWiz (@hollywizzee) - 7h ago

# 滚动加载更多回复
browser action=act request='{"kind":"press","key":"End"}'
sleep 3

# 获取新快照
browser action=snapshot depth=5 refs=role

# 合并所有回复数据
```

### 示例 3: 用户主页数据

```bash
# 打开用户主页
browser action=open targetUrl="https://x.com/elonmusk"

# 等待加载
sleep 5

# 获取快照
browser action=snapshot depth=5 refs=role

# 分析结果：
# ✅ 用户名: Elon Musk (Verified)
# ✅ 帖子数: 98.1K posts
# ✅ 关注: 1,290
# ✅ 粉丝: 235.5M Followers
# ✅ 最新推文列表（3-4 条）
```

---

## 常见问题 (FAQ)

### Q1: 为什么没有触发 Cloudflare 验证？

**A**: OpenClaw 使用真实的 Chrome 浏览器实例（headless: false），伪装成正常用户访问，通常不会触发验证。如果遇到：
1. 增加延迟时间（sleep 10）
2. 使用 Chrome Extension Relay（保持登录状态）
3. 避免短时间内大量请求

### Q2: 如何提高页面加载速度？

**A**: 当前配置 `headless: false`，用于调试和可视化。如果速度是优先考虑：
1. 使用 `headless: true`（需修改 browser 工具配置）
2. 减少 `depth` 值（snapshot depth=3 足够大多数场景）
3. 使用 Jina API 作为主要抓取工具

### Q3: 快照返回的数据如何解析？

**A**: 快照返回的是结构化的 DOM 树，可以用以下方式处理：
- **手动分析**: 查看返回的 JSON 结构
- **正则表达式**: 提取特定模式的文本
- **Python 解析**: 将 JSON 转换为字典，遍历提取
- **专用工具**: Twitter Pipeline 已集成解析逻辑（可参考）

### Q4: 批量抓取是否可行？

**A**: 不推荐大规模批量抓取：
- 速度慢（每条推文 5-10 秒）
- 可能触发 Twitter 的速率限制
- 资源消耗高

**推荐方案**:
- 批量抓取 → Jina API（Twitter Pipeline 已集成）
- 复杂场景 → Playwright
- 混合使用 → 最佳性能

### Q5: 如何处理需要登录的内容？

**A**: 使用 Chrome Extension Relay：
1. 在 Chrome 中登录 X.com
2. 安装 OpenClaw Browser Relay 扩展
3. 在目标标签页点击扩展，启用连接
4. 使用 `profile=chrome` 参数访问

```bash
browser action=open targetUrl="https://x.com/..." profile=chrome
```

---

## 脚本集成示例

### Python 脚本

```python
import time
import json
from pathlib import Path

def fetch_tweet_with_playwright(tweet_url, output_dir="twitter_pipeline/data/tweets"):
    """使用 Playwright 抓取推文"""
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    # 1. 调用 browser 工具（通过 exec 或 subprocess）
    # browser action=start profile=openclaw
    # browser action=open targetUrl="{tweet_url}"
    # sleep 5
    # browser action=snapshot depth=5 refs=role

    # 2. 解析快照数据（假设已获取）
    snapshot_data = {}  # 从 browser 工具获取

    # 3. 提取关键信息
    tweet_info = {
        "url": tweet_url,
        "author": extract_author(snapshot_data),
        "content": extract_content(snapshot_data),
        "stats": extract_stats(snapshot_data),
        "replies": extract_replies(snapshot_data)
    }

    # 4. 保存数据
    tweet_id = extract_tweet_id(tweet_url)
    with open(output_path / f"{tweet_id}.json", 'w') as f:
        json.dump(tweet_info, f, indent=2)

    return tweet_info
```

---

## 性能优化建议

### 1. 批量操作
```bash
# 避免频繁启动/关闭浏览器
browser action=start profile=openclaw

# 批量打开多个推文
for url in tweet_urls:
  browser action=open targetUrl="$url"
  sleep 5
  browser action=snapshot depth=5 refs=role
  # 处理数据...
```

### 2. 缓存机制
```bash
# 检查是否已抓取
if [ ! -f "tweets/123456789.json" ]; then
  browser action=open targetUrl="https://x.com/..."
fi
```

### 3. 延迟优化
```bash
# 根据网络情况调整
sleep 3  # 快速网络
sleep 5  # 正常网络
sleep 10 # 慢速网络/高负载
```

---

## 限制和注意事项

### ⚠️ 当前限制

1. **回复加载**: 需要滚动加载，可能多次操作
2. **媒体内容**: 图片/视频需要额外处理（不能直接嵌入）
3. **批量性能**: 不适合大规模批量抓取
4. **速率限制**: Twitter 可能限制自动化访问

### 🚫 不建议的使用场景

- ❌ 大规模批量抓取（使用 Jina API）
- ❌ 实时监控（频率过高可能被封）
- ❌ 数据挖掘（如需大量数据，考虑官方 API）

---

## 相关资源

### OpenClaw 工具
- `browser` - 浏览器自动化工具
- `web_fetch` - 轻量级页面抓取
- `twitter_pipeline` - Twitter 数据摄取管道

### 官方文档
- Twitter (X.com): https://x.com
- Twitter API: https://developer.twitter.com/en/docs

### 相关 Skill
- twitter_fetcher - Jina API 抓取推文
- agent-browser - 浏览器自动化 CLI

---

## 更新日志

### 2026-02-28
- ✅ 初始版本
- ✅ 基础操作文档
- ✅ 实战示例
- ✅ 与其他工具对比

---

*技能版本*: 1.0.0
*创建时间*: 2026-02-28
*维护者*: Clawd (AI Assistant)