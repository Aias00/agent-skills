# Fund Query - 快速入门

基于天天基金网API的基金净值查询技能。

---

## 5分钟快速开始

### 1. 查询单只基金

```python
import requests
import json
import re

def fetch_fund_data(fund_code):
    url = f"http://fundgz.1234567.com.cn/js/{fund_code}.js"
    response = requests.get(url, headers={"User-Agent": "Mozilla/5.0"})
    text = response.text

    if 'jsonpgz()' in text or not 'jsonpgz(' in text:
        return None

    json_str = re.findall(r'jsonpgz\((.*?)\);', text)[0]
    data = json.loads(json_str)

    return {
        'fund_code': fund_code,
        'fund_name': data['name'],
        'nav': float(data['dwjz']),
        'nav_date': data['jzrq'],
        'estimated_nav': float(data['gsz']),
        'change_pct': float(data['gszzl']),
        'update_time': data['gztime']
    }

# 使用示例
data = fetch_fund_data('016452')
print(f"{data['fund_name']}: {data['nav']} ({data['change_pct']:+.2f}%)")
```

### 2. 批量查询

```python
fund_codes = ['016452', '017641', '270023']
for code in fund_codes:
    data = fetch_fund_data(code)
    if data:
        print(f"{code} {data['fund_name']}: {data['change_pct']:+.2f}%")
```

### 3. Bash命令

```bash
curl -s "http://fundgz.1234567.com.cn/js/016452.js"
```

---

## 常用基金代码

| 类型 | 基金代码 | 基金名称 |
|------|---------|---------|
| 美股 | 016452 | 南方纳指100A |
| 美股 | 017641 | 摩根标普500A |
| 全球 | 270023 | 广发全球精选A |
| 债券 | 110027 | 易方达安心回报债券A |

更多基金代码请参考 `fund_codes.json`

---

## API地址

```
http://fundgz.1234567.com.cn/js/{基金代码}.js
```

**特性**: 免费、公开、实时、无需授权

---

## 完整文档

详见 `SKILL.md` - 包含完整的API说明、错误处理、集成示例等。

---

## 限制和注意事项

⚠️ 估算净值 ≠ 官方净值（投资决策应以官方净值为准）
⚠️ 部分基金可能暂无数据
⚠️ API无官方保证，建议定期测试

---

**Skill位置**: `skills/fund-query/`
**创建时间**: 2026-03-01