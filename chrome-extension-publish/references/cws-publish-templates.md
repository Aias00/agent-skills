# CWS Publish Templates

Use these as editable drafts. Replace product-specific placeholders before submitting.
For generated listing documents, keep both Chinese and English versions together and semantically aligned.

## 0) Store short summary (ZH/EN)

### ZH
在浏览器工具栏快速查看 [核心功能]，支持 [1-2 个关键能力]，帮助用户高效完成 [单一目的]。

### EN
Quickly access [core function] from the browser toolbar, with [1-2 key capabilities] to help users accomplish [single purpose] efficiently.

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

## 3) Permission rationale templates (ZH)

### storage (ZH)
用于在 `chrome.storage.local` 中保存最近行情数据与时间戳缓存，以减少重复请求并提升稳定性。不收集或传输个人用户数据。

### alarms (ZH)
用于安排周期性后台刷新（例如每小时一次），保证展示的行情数据保持最新，无需用户手动刷新。

### Host permissions (ZH)
仅用于请求公开行情数据 API：
- `https://push2.eastmoney.com/*` 用于 AU9999 实时行情数据
- `https://www.sge.com.cn/*` 用于日度历史行情数据  
请求仅限只读数据获取；不注入页面，不在第三方网站执行脚本。

## 4) Permission rationale templates (EN)

### storage (EN)
Used to store local cache for recent market quotes and timestamps in `chrome.storage.local` to reduce repeated requests and improve reliability. No personal user data is collected or transmitted.

### alarms (EN)
Used to schedule periodic background refresh (for example, hourly) so displayed market prices remain current without requiring manual refresh.

### Host permissions (EN)
Used only to request public market data APIs:
- `https://push2.eastmoney.com/*` for AU9999 real-time quote data
- `https://www.sge.com.cn/*` for daily historical market data  
Requests are read-only data fetches; no page injection, no script execution on third-party websites.

## 5) Remote code answer template (ZH/EN)

### ZH
不，本扩展不使用远程代码。  
所有可执行 JavaScript 均随扩展包本地打包。网络访问仅用于获取远程数据（JSON/HTML/text），不执行远程 JS/Wasm，不使用 `eval`，也不进行动态远程模块加载。

### EN
No, this extension does not use remote code.  
All executable JavaScript is packaged in the extension bundle. Network access is used only for fetching remote data (JSON/HTML/text). No remote JS/Wasm execution, `eval`, or dynamic remote module loading is used.

## 6) Data use disclosure template (ZH/EN, no personal data)

### ZH
本扩展不会收集、存储或传输个人用户数据。  
扩展仅获取公开行情数据，并在本地保存非个人缓存数据以提升性能与可靠性。

### EN
This extension does not collect, store, or transmit personal user data.  
It only fetches public market data and stores non-personal cache data locally for performance and reliability.

## 7) Reviewer notes template (ZH/EN)

### ZH
本次提交更新了 [feature/fix summary]。  
权限已最小化为 `storage`、`alarms` 以及获取公开行情数据所需的特定 host 权限。  
不使用远程代码执行。  
不收集或传输个人用户数据。

### EN
This submission updates [feature/fix summary].  
Permissions are minimized to `storage`, `alarms`, and specific host permissions required for public market data fetching.  
No remote code execution is used.  
No personal user data is collected or transmitted.

## 8) Privacy policy update note template (ZH/EN)

### ZH
隐私政策位置：`privacy-policy.md`（扩展根目录，固定文件名）。  
本次版本隐私政策结论：[需要更新 / 无需更新]。  
原因：[权限、数据来源、数据存储、数据流或功能范围是否变化的具体说明]。

### EN
Privacy policy location: `privacy-policy.md` (fixed filename at extension root).  
Privacy policy decision for this release: [update required / not required].  
Reason: [concrete explanation of changes or no-change in permissions, endpoints, storage, data flow, or feature scope].

## 9) Store image asset checklist (publish required)

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
