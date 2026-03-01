# Troubleshooting

## `Playwright is unavailable for auto-capture`

Cause:
- Assets are enabled
- No `--inputs` provided
- Auto-capture fallback is enabled
- Playwright not installed

Fix:
```bash
python3 -m pip install playwright
python3 -m playwright install chromium
```

Or pass explicit image inputs:
```bash
--inputs /abs/path/screenshot-1.png /abs/path/screenshot-2.png
```

## `No icon source found in manifest`

Cause:
- Manifest has no usable icon path and no `--icon-source` provided.

Fix:
```bash
--icon-source /abs/path/icon.png
```

## `Extension has no icons/ folder`

Default behavior:
- `run_e2e_extension_pipeline.py` auto-generates:
  - `icons/icon16.png`
  - `icons/icon48.png`
  - `icons/icon128.png`
- Also updates `manifest.json` mappings (`icons` and `action.default_icon`).

If you want to disable auto-generation:
```bash
--skip-icon-bootstrap
```

## `JS syntax check failed`

Cause:
- Syntax error in extension runtime JS file.

Fix:
- Open the reported file and line.
- Re-run pipeline after correction.
- Use `--skip-js-check` only for emergency bypass.

## `popup UI audit failed`

Cause:
- `popup.html` style wiring is missing, or
- popup width is too small (default guardrail: `< 560px`), or
- CSS contains media reset that sets popup width back to `100%`, or
- icon files are still fallback-generated style.

Fix:
- Ensure `manifest.action.default_popup` exists and popup stylesheet is loaded.
- Set explicit popup width/min-width on `html` or `body` (>= guardrail value).
- Remove media query rules that collapse popup width.
- Replace fallback icon set with custom brand icons.
- Review report:
```bash
release/popup-ui-audit.md
```

Optional bypass (not recommended for release):
```bash
--skip-ui-audit
```

Adjust width guardrail:
```bash
--min-popup-width 620
```

## `popup preview capture failed` (when enabled)

Cause:
- Extension ID could not be resolved in current Chromium mode.
- This happens only when `--capture-popup-preview` is enabled.

Fix:
- Ensure manifest has a valid background service worker and popup path.
- Re-run without headless preview, or keep default (headed) mode.
- Check output target path:
```bash
release/store-assets/screenshots/popup-preview-620x760.png
```

## `pipeline ... failed with exit code`

Cause:
- Underlying publish pipeline step failed.

Fix:
- Read stderr in the same run output.
- Check generated artifacts in `release/`.
- Re-run with narrowed scope:
```bash
--skip-assets
```
or
```bash
--skip-docs
```

## `submit_cws_playwright failed`

Cause:
- `--submit-playwright` enabled but browser automation did not match current CWS UI.
- Login/2FA did not complete within `--submit-login-timeout-ms`.
- Item edit page URL template does not match current dashboard URL pattern.

Fix:
- Re-run with headed mode (default), complete login manually, and keep a persistent profile:
```bash
--submit-playwright --submit-user-data-dir ~/.codex/chrome-webstore-playwright-profile
```
- Increase login wait:
```bash
--submit-login-timeout-ms 600000
```
- Disable final destructive click for verification runs:
```bash
--submit-playwright
```
- Enable final click only after manual confirmation:
```bash
--submit-playwright --submit-for-review
```
