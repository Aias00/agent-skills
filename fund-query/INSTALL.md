# Fund Query Skill - 安装指南

将此skill安装到OpenClaw或AI助手系统的方法。

---

## 方法1: 手动安装（推荐）

### 步骤1: 复制文件

将整个 `fund-query` 文件夹复制到你的skills目录：

```bash
# OpenClaw用户
cp -r fund-query ~/.openclaw/workspace/skills/

# 其他AI助手用户
cp -r fund-query ~/.ai-assistants/skills/
# 或者
cp -r fund-query /path/to/your/skills/directory/
```

### 步骤2: 验证安装

```bash
# 检查文件
ls -la ~/.openclaw/workspace/skills/fund-query/

# 应该看到以下文件:
# SKILL.md
# README.md
# example.py
# fund_codes.json
# INSTALL.md
```

### 步骤3: 测试示例代码

```bash
cd ~/.openclaw/workspace/skills/fund-query
python3 example.py
```

如果测试成功，会看到基金净值查询的输出。

---

## 方法2: 通过ClawHub安装（如果可用）

```bash
# 假设此skill已发布到ClawHub
clawhub install fund-query
```

---

## 依赖项

### 必需依赖

- Python 3.6+
- requests库

### 安装依赖

```bash
pip3 install requests
```

或者如果使用OpenClaw的Python环境：

```bash
# Homebrew Python
pip3 install requests

# 或使用系统的python3
python3 -m pip install requests --user
```

---

## 配置

### 无需配置

此skill使用公开免费的API，无需任何API Key或配置文件。

---

## 使用方法

### 1. 直接导入使用

```python
from skills.fund-query.example import fetch_fund_data, fetch_multiple_funds

# 查询单只基金
data = fetch_fund_data('016452')
print(data)

# 批量查询
funds = fetch_multiple_funds(['016452', '017641'])
for fund in funds:
    print(fund)
```

### 2. 运行示例脚本

```bash
cd ~/.openclaw/workspace/skills/fund-query
python3 example.py
```

### 3. 在OpenClaw中使用

可以直接询问AI助手：

```
帮我查询基金016452的净值
```

或

```
查询我的所有基金的最新净值：016452, 017641, 270023
```

---

## 卸载

```bash
# 删除skill目录
rm -rf ~/.openclaw/workspace/skills/fund-query
```

---

## 故障排除

### 问题1: requests模块不存在

**错误**: `ModuleNotFoundError: No module named 'requests'`

**解决**:
```bash
pip3 install requests
```

### 问题2: API请求超时

**错误**: `requests.exceptions.Timeout`

**解决**: 检查网络连接，或增加超时时间：

```python
response = requests.get(url, headers=headers, timeout=20)  # 增加到20秒
```

### 问题3: 返回空数据

**错误**: 基金返回 `jsonpgz();`

**原因**:
- 基金代码错误
- 基金暂停交易
- API暂时故障

**解决**: 确认基金代码是否正确，或稍后重试。

---

## 更新

获取最新版本：

```bash
cd ~/.openclaw/workspace/skills/fund-query
git pull origin main  # 如果使用Git管理
```

或重新复制整个文件夹。

---

## 支持和反馈

如有问题或建议，请联系：
- OpenClaw Discord: https://discord.com/invite/clawd
- GitHub Issues: https://github.com/openclaw/skills

---

## 许可证

此skill专为OpenClaw设计，遵循OpenClaw许可证。

---

**Skill版本**: 1.0.0
**创建时间**: 2026-03-01
**作者**: AI Assistant