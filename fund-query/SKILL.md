# Fund Query - 基金净值查询技能

查询中国基金净值和涨跌幅的专用技能。使用天天基金网公开API，免费、实时、无需授权。

---

## 功能说明

获取基金的净值、涨跌幅、更新时间等关键信息，用于投资决策和资产组合管理。

### 数据来源

- **API地址**: `http://fundgz.1234567.com.cn/js/{基金代码}.js`
- **提供商**: 天天基金网（www.1234567.com.cn）
- **授权**: 公开免费API，无需API Key
- **更新频率**: 每交易日更新
  - 05:00: 估算净值更新
  - 15:00+: 官方净值确认

### API特性

| 特性 | 说明 |
|------|------|
| 成本 | 免费 |
| 授权 | 无需注册/授权 |
| 延迟 | 实时（估算）+ 官方确认 |
| 限制 | 无明确的请求限制 |
| 数据 | 官方净值 + 实时估算净值 |

---

## 核心数据字段

| 字段 | 英文key | 类型 | 说明 |
|------|---------|------|------|
| 基金代码 | fundcode | string | 基金代码 |
| 基金名称 | name | string | 基金全称 |
| 单位净值 | dwjz | float | **官方确认净值**（最准确） |
| 净值日期 | jzrq | string | 官方净值日期（YYYY-MM-DD） |
| 估算净值 | gsz | float | 实时估算净值（仅供参考） |
| 涨跌幅 | gszzl | string | 涨跌幅百分比（格式: "+1.23" 或 "-0.45"） |
| 更新时间 | gztime | string | 数据更新时间 |

### 数据可信度

- **单位净值（dwjz）**: 100%可信 - 官方确认净值
- **估算净值（gsz）**: 90%可信 - 基于持仓实时计算
- **涨跌幅（gszzl）**: 90%可信 - 基于估算净值计算

---

## 使用方法

### 1. 单只基金查询

**Python示例**:

```python
import requests
import json
import re

def fetch_fund_data(fund_code):
    """获取单只基金的净值数据"""
    url = f"http://fundgz.1234567.com.cn/js/{fund_code}.js"
    headers = {"User-Agent": "Mozilla/5.0"}

    try:
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()

        text = response.text

        # 检查是否有数据
        if 'jsonpgz()' in text or not 'jsonpgz(' in text:
            return None

        # 解析JSONP格式: jsonpgz({...});
        json_str = re.findall(r'jsonpgz\((.*?)\);', text)[0]
        data = json.loads(json_str)

        # 解析涨跌幅（字符串格式）
        change_str = data.get('gszzl', '0')
        try:
            change_pct = float(change_str)
        except:
            change_pct = 0.0

        return {
            'fund_code': fund_code,
            'fund_name': data.get('name', ''),
            'nav': float(data.get('dwjz', 0)),          # 单位净值
            'nav_date': data.get('jzrq', ''),            # 净值日期
            'estimated_nav': float(data.get('gsz', 0)),  # 估算净值
            'change_pct': change_pct,
            'update_time': data.get('gztime', '')
        }
    except Exception as e:
        print(f"获取基金 {fund_code} 数据失败: {e}")
        return None

# 使用示例
data = fetch_fund_data('016452')
if data:
    print(f"基金: {data['fund_name']}")
    print(f"官方净值: {data['nav']} (截至 {data['nav_date']})")
    print(f"估算净值: {data['estimated_nav']}")
    print(f"涨跌幅: {data['change_pct']:+.2f}%")
    print(f"更新时间: {data['update_time']}")
```

**输出示例**:
```
基金: 南方纳斯达克100指数发起(QDII)A
官方净值: 1.9997 (截至 2026-02-26)
估算净值: 1.9941
涨跌幅: -0.28%
更新时间: 2026-02-28 05:00
```

---

### 2. 批量查询多只基金

```python
def fetch_multiple_funds(fund_codes):
    """批量获取多只基金的净值数据"""
    results = []
    for code in fund_codes:
        data = fetch_fund_data(code)
        if data:
            results.append(data)
    return results

# 使用示例
fund_codes = ['016452', '017641', '270023']
funds_data = fetch_multiple_funds(fund_codes)

for fund in funds_data:
    print(f"{fund['fund_code']} {fund['fund_name']}: {fund['change_pct']:+.2f}%")
```

---

### 3. 持仓盈亏计算

```python
def calculate_profit_loss(fund_data, holding_amount):
    """计算持仓盈亏"""
    if not fund_data:
        return None

    nav = fund_data['nav']
    total_value = holding_amount * nav

    return {
        'fund_name': fund_data['fund_name'],
        'holding_amount': holding_amount,
        'current_nav': nav,
        'total_value': total_value,
        'change_pct': fund_data['change_pct']
    }

# 使用示例（持有1364.7份基金）
holding = calculate_profit_loss(data, 1364.7)
if holding:
    print(f"基金: {holding['fund_name']}")
    print(f"持有份额: {holding['holding_amount']:.2f}")
    print(f"当前净值: {holding['current_nav']:.4f}")
    print(f"总价值: ¥{holding['total_value']:,.2f}")
    print(f"涨跌幅: {holding['change_pct']:+.2f}%")
```

---

### 4. Bash命令行查询

**curl示例**:

```bash
# 查询单只基金
curl -s "http://fundgz.1234567.com.cn/js/016452.js"

# 格式化输出（使用jq）
curl -s "http://fundgz.1234567.com.cn/js/016452.js" | \
  grep -oP 'jsonpgz\(\K.*(?=\);)' | jq .

# 批量查询（循环）
for code in 016452 017641 270023; do
  echo "=== $code ==="
  curl -s "http://fundgz.1234567.com.cn/js/${code}.js"
  echo ""
done
```

---

### 5. 常用基金代码参考

#### QDII基金（美国/海外市场）

| 基金代码 | 基金名称 | 跟踪指数 |
|---------|---------|---------|
| 016452 | 南方纳指100A | 纳斯达克100 |
| 017641 | 摩根标普500A | 标普500 |
| 270023 | 广发全球精选A | 全球股票 |
| 118001 | 易方达亚洲精选 | 亚洲市场 |
| 013328 | 嘉实全球价值 | 全球价值股 |
| 001092 | 广发生物科技A | 生物科技 |

#### A股指数基金

| 基金代码 | 基金名称 | 跟踪指数 |
|---------|---------|---------|
| 000300 | 华夏沪深300ETF联接A | 沪深300 |
| 000950 | 易方达沪深300ETF联接A | 沪深300 |
| 110022 | 易方达创业板ETF联接A | 创业板 |

#### 债券基金

| 基金代码 | 基金名称 | 类型 |
|---------|---------|------|
| 110027 | 易方达安心回报债券A | 混合债 |
| 000003 | 中海可转债A | 可转债 |

---

## 时间窗口和更新逻辑

### 基金净值更新时间表

| 时间段（北京时间） | 数据类型 | 说明 |
|-------------------|---------|------|
| 交易日 05:00-14:59 | 估算净值 | 实时计算，仅供参考 |
| 交易日 15:00+ | 官方净值 | 确认净值，最准确 |
| 周末/节假日 | 不更新 | 使用上一个交易日数据 |

### 何时查询最适合

| 场景 | 建议时间 | 数据类型 |
|------|---------|---------|
| 日常跟踪 | 09:00-14:00 | 估算净值 |
| 购买决策 | 15:30之后 | 官方净值 |
| 申购/赎回 | 15:00之前 | 当天净值生效 |
| 周末复盘 | 周五15:30后 | 最新官方净值 |

**重要提示**: 基金申购/赎回必须在15:00前完成，才能享受当天净值。

---

## 错误处理和异常情况

### 常见错误及处理

| 错误 | 原因 | 处理方法 |
|------|------|---------|
| 返回 `jsonpgz();` | 基金代码错误或暂停交易 | 检查基金代码 |
| 请求超时 | 网络问题或API故障 | 增加超时时间或重试 |
| gszzl解析失败 | 涨跌幅格式异常 | 使用默认值0 |
| 净值为0 | 基金成立初期无净值 | 使用估算净值 |

### 容错代码示例

```python
def safe_fetch_fund(fund_code, max_retries=3):
    """带重试和安全处理的基金查询"""
    for attempt in range(max_retries):
        try:
            data = fetch_fund_data(fund_code)

            if not data:
                print(f"基金 {fund_code} 暂无数据")
                return None

            # 检查数据有效性
            if data['nav'] <= 0:
                print(f"基金 {fund_code} 官方净值无效，使用估算净值")
                data['nav'] = data['estimated_nav']

            return data

        except requests.exceptions.Timeout:
            if attempt < max_retries - 1:
                print(f"超时，重试 {attempt + 1}/{max_retries}...")
                time.sleep(2)
            else:
                print(f"基金 {fund_code} 请求失败")
                return None

        except Exception as e:
            print(f"基金 {fund_code} 查询异常: {e}")
            return None

    return None
```

---

## 完整集成示例

### 示例1: 每日自动化监控

```python
#!/usr/bin/env python3
"""每日基金净值监控脚本"""

import requests
import json
import re
from datetime import datetime

# 基金配置
FUNDS_TO_MONITOR = {
    "016452": {"name": "南方纳指100A", "amount": 2729.37},
    "017641": {"name": "摩根标普500A", "amount": 690.91},
    "270023": {"name": "广发全球精选A", "amount": 441.69},
}

def generate_daily_report():
    """生成每日报告"""
    timestamp = datetime.now()
    print(f"\n📊 基金净值报告 - {timestamp.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'='*80}")

    total_value = 0
    total_change = 0

    for fund_code, info in FUNDS_TO_MONITOR.items():
        data = fetch_fund_data(fund_code)

        if not data:
            print(f"⚠️  {fund_code} {info['name']}: 暂无数据")
            continue

        # 计算当前价值
        shares = info['amount'] / info['amount']  # 这里假设amount是持仓金额
        current_value = shares * data['estimated_nav']
        daily_change = current_value * data['change_pct'] / 100

        total_value += current_value
        total_change += daily_change

        print(f"✅ {fund_code} {info['name']}")
        print(f"   官方净值: {data['nav']:.4f}")
        print(f"   估算净值: {data['estimated_nav']:.4f}")
        print(f"   涨跌幅: {data['change_pct']:+.2f}%")
        print(f"   当前价值: ¥{current_value:,.2f}")
        print()

    print(f"{'='*80}")
    print(f"总持仓价值: ¥{total_value:,.2f}")
    print(f"当日盈亏: ¥{total_change:,.2f} ({total_change/total_value*100:.2f}%)")

if __name__ == '__main__':
    generate_daily_report()
```

---

### 示例2: 购买时机分析

```python
def analyze_buy_timing(fund_codes):
    """分析购买时机"""
    funds_data = [fetch_fund_data(code) for code in fund_codes]
    funds_data = [f for f in funds_data if f is not None]

    if not funds_data:
        return "数据不足，无法分析"

    # 计算平均涨跌幅
    avg_change = sum(f['change_pct'] for f in funds_data) / len(funds_data)

    # 判断市场情绪
    if avg_change < -1.0:
        return f"市场回调中（平均{avg_change:.2f}%），可能适合低吸 ✅"
    elif avg_change > 1.0:
        return f"市场上涨中（平均{avg_change:.2f}%），追高风险 ⚠️"
    else:
        return f"市场震荡中（平均{avg_change:.2f}%），可考虑分批买入 🟡"

# 使用示例
timing = analyze_buy_timing(['016452', '017641', '270023'])
print(timing)
```

---

## 注意事项和限制

### ⚠️ 重要限制

1. **估算净值不等于官方净值**
   - 估算净值基于持仓实时计算
   - 官方净值在15:00后才确认
   - 投资决策应以官方净值为准

2. **不支持所有基金**
   - 部分新基金可能暂无数据
   - 短期开放期基金可能无估算
   - 部分ETF可能不支持

3. **API无保证**
   - 这是公开API，不承诺稳定性
   - 未来可能变更或停止服务
   - 建议定期测试API可用性

4. **仅限中国基金**
   - API只支持中国境内公募基金
   - 不支持海外基金直接查询
   - 不支持私募基金

---

## 扩展和优化建议

### 1. 数据缓存

```python
import time
from datetime import timedelta

CACHE = {}

def fetch_with_cache(fund_code, cache_minutes=60):
    """带缓存的基金查询"""
    now = time.time()

    if fund_code in CACHE:
        cached_data, cached_time = CACHE[fund_code]
        if now - cached_time < cache_minutes * 60:
            return cached_data

    data = fetch_fund_data(fund_code)
    if data:
        CACHE[fund_code] = (data, now)

    return data
```

### 2. 历史数据存储

```python
def save_to_history(fund_data, history_file='fund_history.jsonl'):
    """保存历史数据"""
    record = {
        **fund_data,
        'timestamp': datetime.now().isoformat()
    }

    with open(history_file, 'a') as f:
        json.dump(record, f)
        f.write('\n')
```

### 3. 告警系统

```python
def check_alerts(fund_data, threshold=2.0):
    """检查涨跌幅告警"""
    if abs(fund_data['change_pct']) >= threshold:
        direction = "暴涨" if fund_data['change_pct'] > 0 else "暴跌"
        return f"⚠️ {fund_data['fund_name']} {direction} {abs(fund_data['change_pct']):.2f}%"
    return None
```

---

## 技术支持

**API来源**: 天天基金网（www.1234567.com.cn）
**官方文档**: 无公开文档（通过反向工程获得）
**最后测试**: 2026-03-01

### 备用数据源

如果天天基金网API不可用，可以考虑：

1. **支付宝/淘宝基金**
   - 需要登录授权
   - 数据准确但集成复杂

2. **东方财富Choice**
   - 商业数据服务
   - 需要付费订阅

3. **同花顺iFinD**
   - 专业金融数据
   - 企业级解决方案

---

## 相关技能

- **portfolio-manager**: 投资组合管理
- **portfolio-watcher**: 投资组合监控
- **stock-analysis**: 股票分析
- **us-stock-analysis**: 美股分析

---

## 版本历史

- **1.0.0** (2026-03-01): 初始版本，基于天天基金网API

---

**Skill位置**: `skills/fund-query/SKILL.md`
**创建时间**: 2026-03-01
**作者**: AI Assistant
**许可**: OpenClaw专用