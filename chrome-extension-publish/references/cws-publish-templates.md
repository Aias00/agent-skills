# CWS Publish Templates

Use these as editable drafts. Replace product-specific placeholders before submitting.

## 1) Chinese listing description (long)

`Gold Price Monitor` 用于在浏览器工具栏实时查看国内投资金价（AU9999），并在弹窗中展示近 7 天价格趋势与历史记录。  
核心功能：  
1. 实时价格展示：查看当前价格、涨跌额和涨跌幅。  
2. 趋势图与历史：展示近期价格走势和按日期排列的历史记录。  
3. 自动刷新：后台定时刷新行情数据，并支持手动刷新。  
4. 本地缓存：网络波动时优先使用本地缓存，保证可用性。  
本扩展仅提供行情信息展示，不提供交易功能，不构成投资建议。

## 2) English listing description (long)

`Gold Price Monitor` helps users quickly view domestic investment gold prices (AU9999) in the browser toolbar and popup.  
Key features:  
1. Real-time price display with price change and percentage change.  
2. 7-day trend chart and historical records.  
3. Scheduled background refresh with manual refresh support.  
4. Local cache fallback for improved reliability during network instability.  
This extension is for market information display only. It does not provide trading features or investment advice.

## 3) Permission rationale templates

### storage
Used to store local cache for recent market quotes and timestamps in `chrome.storage.local` to reduce repeated requests and improve reliability. No personal user data is collected or transmitted.

### alarms
Used to schedule periodic background refresh (for example, hourly) so displayed market prices remain current without requiring manual refresh.

### Host permissions
Used only to request public market data APIs:
- `https://push2.eastmoney.com/*` for AU9999 real-time quote data
- `https://www.sge.com.cn/*` for daily historical market data  
Requests are read-only data fetches; no page injection, no script execution on third-party websites.

## 4) Remote code answer template

No, this extension does not use remote code.  
All executable JavaScript is packaged in the extension bundle. Network access is used only for fetching remote data (JSON/HTML/text). No remote JS/Wasm execution, `eval`, or dynamic remote module loading is used.

## 5) Data use disclosure template (no personal data)

This extension does not collect, store, or transmit personal user data.  
It only fetches public market data and stores non-personal cache data locally for performance and reliability.

## 6) Reviewer notes template

This submission updates [feature/fix summary].  
Permissions are minimized to `storage`, `alarms`, and specific host permissions required for public market data fetching.  
No remote code execution is used.  
No personal user data is collected or transmitted.

## 7) Store image asset checklist (publish required)

Prepare images under `release/store-assets/`:

- `release/store-assets/icon-128x128.png`  
  - Size: `128x128`  
  - Format: `PNG`
  - Use: Chrome Web Store icon

- `release/store-assets/screenshots/*.png|jpg|jpeg`  
  - Count: `1-5`  
  - Size: `1280x800` (preferred) or `640x400`

- `release/store-assets/small-promo-440x280.png` (or `.jpg/.jpeg`)  
  - Size: `440x280`  
  - Use: small promo tile

- `release/store-assets/marquee-1400x560.png` (or `.jpg/.jpeg`, optional)  
  - Size: `1400x560`  
  - Use: marquee promo tile

Validation command:

```bash
python3 scripts/validate_store_assets.py --root release/store-assets
```
