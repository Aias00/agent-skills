# Notion Skill 安装说明

## 📦 文件清单

```
notion_skill_pack/
├── SKILL.md          # Notion Skill文档
└── README.md         # 本文件
```

---

## 🔧 安装步骤

### 方法1：手动安装（推荐）

1. 创建skill目录:
```bash
mkdir -p ~/.openclaw/skills/notion
```

2. 复制SKILL.md:
```bash
cp SKILL.md ~/.openclaw/skills/notion/SKILL.md
```

3. 配置API Key:
```bash
# 1. 访问 https://notion.so/my-integrations 创建integration
# 2. 复制API key (以 ntn_ 或 secret_ 开头)
mkdir -p ~/.config/notion
echo "ntn_your_key_here" > ~/.config/notion/api_key
```

4. 重启OpenClaw或重新加载skills:
```bash
openclaw skills reload
```

5. 验证安装:
```bash
openclaw skills list | grep notion
```

---

### 方法2：使用ClawHub安装

如果ClawHub上有notion skill:

```bash
clawhub install notion
```

---

## 🚀 使用示例

安装完成后，可以这样使用：

```
1. 创建页面:
   "在Notion中创建一个新页面，标题是'待办事项'"

2. 查询数据库:
   "查询我的Notion数据库中所有状态为Active的项目"

3. 搜索页面:
   "搜索标题包含'基金'的页面"

4. 更新页面:
   "将页面状态更新为Done"
```

---

## ⚙️ 配置说明

**必需的环境变量**:
- `NOTION_API_KEY` - Notion Integration API Key

**配置路径**:
- `~/.config/notion/api_key`

**分享权限**:
- 在Notion中，需要将页面/数据库分享给你的integration
- 点击页面/数据库右上角 "..." → "Connect to" → 选择你的integration

---

## 📚 Skill功能

**支持的操作**:
- ✅ 创建页面 (Pages)
- ✅ 读取页面内容和块 (Blocks)
- ✅ 更新页面属性
- ✅ 创建/查询数据库 (Data Sources)
- ✅ 搜索页面和数据库
- ✅ 添加内容块到页面

**API版本**: 2025-09-03 (最新)

---

## 🔍 API文档

详细的API文档请查看 `SKILL.md` 文件。

关键端点:
- `POST /v1/search` - 搜索
- `GET /v1/pages/{id}` - 获取页面
- `POST /v1/pages` - 创建页面
- `PATCH /v1/pages/{id}` - 更新页面
- `POST /v1/data_sources/{id}/query` - 查询数据库

---

## ⚠️ 注意事项

1. **两个ID概念**（Notion 2025-09-03版本）:
   - `database_id` - 用于创建页面
   - `data_source_id` - 用于查询数据库

2. **速率限制**: 约每秒3次请求

3. **权限设置**: 必须在Notion中分享页面/数据库给integration

---

## 📞 问题排查

### 找不到skill
```bash
openclaw skills list | grep notion
```

### API Key错误
```bash
cat ~/.config/notion/api_key
# 确认格式正确 (ntn_xxx 或 secret_xxx)
```

### 权限被拒
- 检查Notion中是否分享了页面/数据库给integration

---

**版本**: 1.0
**更新时间**: 2026-03-02
**维护者**: Clawd