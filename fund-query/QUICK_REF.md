# Fund Query Skill - 快速参考卡

## 📌 核心信息

**Skill名称**: Fund Query（基金净值查询）
**版本**: 1.0.0
**创建时间**: 2026-03-01
**文件大小**: 27.5KB（未压缩）
**打包文件**:
- ZIP: 12KB
- TAR.GZ: 8.4KB

---

## 🎯 一句话描述

使用天天基金网公开API查询中国公募基金净值和涨跌幅，免费、实时、无需授权。

---

## ⚡ 5秒上手

```python
import requests, json, re

url = "http://fundgz.1234567.com.cn/js/016452.js"
data = json.loads(re.findall(r'jsonpgz\((.*?)\);', requests.get(url).text)[0])

print(f"{data['name']}: {data['dwjz']} ({data['gszzl']}%)")
# 输出: 南方纳斯达克100指数发起(QDII)A: 1.9997 (-0.28%)
```

---

## 📊 API地址

```
http://fundgz.1234567.com.cn/js/{基金代码}.js
```

---

## 🔑 关键字段

| 字段 | 说明 | 例子 |
|------|------|------|
| `dwjz` | 单位净值（官方） | 1.9997 |
| `gsz` | 估算净值（实时） | 1.9941 |
| `gszzl` | 涨跌幅 | "-0.28" |
| `jzrq` | 净值日期 | "2026-02-26" |
| `gztime` | 更新时间 | "2026-02-28 05:00" |

---

## 📋 常用基金代码

| 代码 | 名称 | 跟踪指数 |
|------|------|---------|
| 016452 | 南方纳指100A | 纳斯达克100 |
| 017641 | 摩根标普500A | 标普500 |
| 270023 | 广发全球精选A | 全球股票 |
| 118001 | 易方达亚洲精选 | 亚洲市场 |
| 013328 | 嘉实全球价值 | 全球价值股 |
| 001092 | 广发生物科技A | 生物科技 |
| 110027 | 易方达安心回报债券A | 混合债 |

---

## 📁 打包文件清单

```
fund-query-skill-1.0.0.zip (12KB)
└── fund-query/
    ├── SKILL.md (13KB)        # 完整文档
    ├── README.md (2KB)        # 快速入门
    ├── INSTALL.md (3KB)       # 安装指南
    ├── example.py (5.6KB)     # 示例代码
    └── fund_codes.json (2.9KB)# 基金代码库
```

---

## 🔧 依赖项

```bash
pip3 install requests
```

---

## ✅ 验证安装

```bash
cd ~/.openclaw/workspace/skills/fund-query
python3 example.py
```

---

## ⚠️ 限制

1. 估算净值 ≠ 官方净值
2. 部分基金可能无数据
3. API无官方保证

---

## 📞 支持文档

- SKILL.md - 完整文档
- README.md - 快速入门
- INSTALL.md - 安装指南
- example.py - 可运行示例

---

**作者**: AI Assistant
**许可**: OpenClaw专用