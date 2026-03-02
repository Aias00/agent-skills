#!/usr/bin/env python3
"""
基金净值查询示例代码

使用天天基金网API查询基金的净值、涨跌幅等信息
"""

import requests
import json
import re
from typing import Optional, Dict, List


def fetch_fund_data(fund_code: str) -> Optional[Dict]:
    """
    获取单只基金的净值数据

    Args:
        fund_code: 基金代码，如 '016452'

    Returns:
        基金数据字典，包含净值、涨跌幅等信息；失败返回None
    """
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


def fetch_multiple_funds(fund_codes: List[str]) -> List[Dict]:
    """
    批量获取多只基金的净值数据

    Args:
        fund_codes: 基金代码列表

    Returns:
        基金数据列表
    """
    results = []
    for code in fund_codes:
        data = fetch_fund_data(code)
        if data:
            results.append(data)
    return results


def format_fund_data(data: Dict) -> str:
    """格式化基金数据为易读字符串"""
    if not data:
        return "暂无数据"

    return (
        f"基金: {data['fund_name']} ({data['fund_code']})\n"
        f"  官方净值: {data['nav']:.4f} (截至 {data['nav_date']})\n"
        f"  估算净值: {data['estimated_nav']:.4f}\n"
        f"  涨跌幅: {data['change_pct']:+.2f}%\n"
        f"  更新时间: {data['update_time']}"
    )


def calculate_profit_loss(fund_data: Dict, holding_shares: float) -> Optional[Dict]:
    """
    计算持仓盈亏

    Args:
        fund_data: 基金数据
        holding_shares: 持有份额

    Returns:
        盈亏信息字典
    """
    if not fund_data:
        return None

    nav = fund_data['estimated_nav']  # 使用估算净值计算实时价值
    total_value = holding_shares * nav

    return {
        'fund_name': fund_data['fund_name'],
        'holding_shares': holding_shares,
        'current_nav': nav,
        'total_value': total_value,
        'change_pct': fund_data['change_pct']
    }


def generate_report(fund_codes: List[str]) -> str:
    """
    生成基金净值报告

    Args:
        fund_codes: 基金代码列表

    Returns:
        格式化的报告字符串
    """
    print("📡 获取基金数据...")
    funds = fetch_multiple_funds(fund_codes)

    if not funds:
        return "⚠️ 所有基金数据获取失败"

    report = []
    report.append("=" * 80)
    report.append("基金净值报告")
    report.append("=" * 80)
    report.append("")

    for fund in funds:
        report.append(f"✅ {fund['fund_name']} ({fund['fund_code']})")
        report.append(f"   官方净值: {fund['nav']:.4f}")
        report.append(f"   估算净值: {fund['estimated_nav']:.4f}")
        report.append(f"   涨跌幅: {fund['change_pct']:+.2f}%")
        report.append(f"   净值日期: {fund['nav_date']}")
        report.append(f"   更新时间: {fund['update_time']}")
        report.append("")

    # 计算平均涨跌幅
    avg_change = sum(f['change_pct'] for f in funds) / len(funds)
    report.append("-" * 80)
    report.append(f"平均涨跌幅: {avg_change:+.2f}%")

    return "\n".join(report)


def main():
    """主函数 - 示例用法"""

    print("\n📊 基金净值查询示例\n")
    print("=" * 80)
    print()

    # 示例1: 查询单只基金
    print("示例1: 查询单只基金")
    print("-" * 80)
    fund_data = fetch_fund_data('016452')
    if fund_data:
        print(format_fund_data(fund_data))
    else:
        print("⚠️ 基金数据获取失败")
    print()

    # 示例2: 批量查询
    print("示例2: 批量查询多只基金")
    print("-" * 80)
    fund_codes = ['016452', '017641', '270023']
    funds = fetch_multiple_funds(fund_codes)
    for fund in funds:
        print(f"{fund['fund_code']:<10} {fund['fund_name']:<30} {fund['change_pct']:+.2f}%")
    print()

    # 示例3: 计算持仓盈亏
    print("示例3: 计算持仓盈亏（假设持有1364.7份）")
    print("-" * 80)
    if fund_data:
        pl = calculate_profit_loss(fund_data, 1364.7)
        if pl:
            print(f"基金: {pl['fund_name']}")
            print(f"持有份额: {pl['holding_shares']:.2f}")
            print(f"当前净值: {pl['current_nav']:.4f}")
            print(f"总价值: ¥{pl['total_value']:,.2f}")
            print(f"涨跌幅: {pl['change_pct']:+.2f}%")
    print()

    # 示例4: 生成完整报告
    print("示例4: 生成完整报告")
    print("-" * 80)
    report = generate_report(['016452', '017641', '270023', '013328', '001092'])
    print(report)
    print()


if __name__ == '__main__':
    main()