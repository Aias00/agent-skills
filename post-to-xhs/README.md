# post-to-xhs-share

一个可分享的小红书发布 skill 包，核心能力是通过 Chrome DevTools Protocol 控制 Chrome，在小红书创作中心完成登录、上传图文、填写标题正文和点击发布。

## 包内容

- `SKILL.md`
  OpenClaw/Codex skill 说明。
- `scripts/cdp_publish.py`
  CDP 直连 Chrome 的核心发布脚本。
- `scripts/chrome_launcher.py`
  启动带远程调试端口的 Chrome。
- `scripts/account_manager.py`
  管理多账号 Chrome profile。
- `scripts/publish_pipeline.py`
  图文发布流水线脚本。
- `scripts/image_downloader.py`
  下载远程图片到本地。
- `config/accounts.json`
  账号配置模板，已清理为不含真实 profile 路径。
- `references/publish-workflow.md`
  页面流程和选择器说明。

## 依赖

- macOS 或 Windows
- Python 3.10+
- Google Chrome
- Node.js 18+

Python 依赖：

```bash
pip install -r requirements.txt
```

Node 依赖：

```bash
cd scripts
npm install
```

## 首次使用

### 1. 配置账号

编辑 `config/accounts.json`，把 `profile_dir` 改成自己的 Chrome profile 目录，或者直接留空，交给脚本自动初始化。

### 2. 打开登录页

```bash
cd scripts
python3 cdp_publish.py login
```

这一步会启动专用 Chrome，并打开小红书创作中心登录页。扫码完成登录。

### 3. 检查登录状态

```bash
python3 cdp_publish.py check-login
```

## 发布示例

### 图文发布

```bash
cd scripts
python3 cdp_publish.py publish \
  --title "OpenClaw 的一个真实应用案例" \
  --content "这里放正文内容" \
  --images "/absolute/path/to/image1.jpg"
```

### 从文件读取正文

```bash
cd scripts
python3 cdp_publish.py publish \
  --title "OpenClaw 的一个真实应用案例" \
  --content-file "/absolute/path/to/content.txt" \
  --images "/absolute/path/to/image1.jpg"
```

### 仅检查登录

```bash
cd scripts
python3 cdp_publish.py check-login
```

## 注意事项

- 这个包不包含任何真实账号 cookie、Chrome profile、已登录态。
- `config/accounts.json` 已经清理过，发给别人前不需要再删账号信息。
- 页面选择器依赖小红书创作中心 DOM，页面改版后可能需要更新脚本。
- 如果要在 macOS 上用，确认本机 Chrome 路径存在：
  `/Applications/Google Chrome.app/Contents/MacOS/Google Chrome`

## 建议分享方式

建议把整个目录打包发给别人，不要只发 `cdp_publish.py`，因为它依赖：

- `chrome_launcher.py`
- `account_manager.py`
- `config/accounts.json`
- `references/publish-workflow.md`

## 已清理的敏感项

- 真实 `profile_dir`
- 临时生成的 `title.txt`
- 临时生成的 `content.txt`
- 运行时登录态

