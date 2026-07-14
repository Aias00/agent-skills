import fs from 'node:fs';
import path from 'node:path';
import os from 'node:os';
import { spawnSync } from 'node:child_process';
import process from 'node:process';
import { fileURLToPath } from 'node:url';
import { launchChrome, tryConnectExisting, findExistingChromeDebugPort, getPageSession, waitForNewTab, clickElement, typeText, evaluate, sleep, type ChromeSession, type CdpConnection } from './cdp.ts';
import { prepareWechatCoverPath } from './cover-utils.ts';
import { normalizePreferredFormatterTheme, renderMarkdownWithPreferredFormatter } from './preferred-markdown-render.ts';
import { loadWechatPublisherExtendConfig } from './wechat-extend-config.ts';

const WECHAT_URL = 'https://mp.weixin.qq.com/';

interface ImageInfo {
  placeholder: string;
  localPath: string;
  originalPath: string;
}

interface ArticleOptions {
  title: string;
  content?: string;
  htmlFile?: string;
  markdownFile?: string;
  coverPath?: string;
  theme?: string;
  color?: string;
  author?: string;
  summary?: string;
  images?: string[];
  contentImages?: ImageInfo[];
  submit?: boolean;
  profileDir?: string;
  cdpPort?: number;
}

interface ExtendConfig {
  defaultTheme?: string;
  defaultColor?: string;
  defaultAuthor?: string;
  chromeProfilePath?: string;
}

function loadExtendConfig(): ExtendConfig {
  return loadWechatPublisherExtendConfig();
}

async function waitForLogin(session: ChromeSession, timeoutMs = 120_000): Promise<boolean> {
  const start = Date.now();
  while (Date.now() - start < timeoutMs) {
    const url = await evaluate<string>(session, 'window.location.href');
    if (url.includes('/cgi-bin/home')) return true;
    await sleep(2000);
  }
  return false;
}

async function waitForElement(session: ChromeSession, selector: string, timeoutMs = 10_000): Promise<boolean> {
  const start = Date.now();
  while (Date.now() - start < timeoutMs) {
    const found = await evaluate<boolean>(session, `!!document.querySelector('${selector}')`);
    if (found) return true;
    await sleep(500);
  }
  return false;
}

async function clickMenuByText(session: ChromeSession, text: string): Promise<void> {
  console.log(`[wechat] Clicking "${text}" menu...`);
  const posResult = await session.cdp.send<{ result: { value: string } }>('Runtime.evaluate', {
    expression: `
      (function() {
        const items = document.querySelectorAll('.new-creation__menu .new-creation__menu-item');
        for (const item of items) {
          const title = item.querySelector('.new-creation__menu-title');
          if (title && title.textContent?.trim() === '${text}') {
            item.scrollIntoView({ block: 'center' });
            const rect = item.getBoundingClientRect();
            return JSON.stringify({ x: rect.x + rect.width / 2, y: rect.y + rect.height / 2 });
          }
        }
        return 'null';
      })()
    `,
    returnByValue: true,
  }, { sessionId: session.sessionId });

  if (posResult.result.value === 'null') throw new Error(`Menu "${text}" not found`);
  const pos = JSON.parse(posResult.result.value);

  await session.cdp.send('Input.dispatchMouseEvent', { type: 'mousePressed', x: pos.x, y: pos.y, button: 'left', clickCount: 1 }, { sessionId: session.sessionId });
  await sleep(100);
  await session.cdp.send('Input.dispatchMouseEvent', { type: 'mouseReleased', x: pos.x, y: pos.y, button: 'left', clickCount: 1 }, { sessionId: session.sessionId });
}

async function copyImageToClipboard(imagePath: string): Promise<void> {
  const __filename = fileURLToPath(import.meta.url);
  const __dirname = path.dirname(__filename);
  const copyScript = path.join(__dirname, './copy-to-clipboard.ts');
  const result = spawnSync('npx', ['-y', 'bun', copyScript, 'image', imagePath], { stdio: 'inherit' });
  if (result.status !== 0) throw new Error(`Failed to copy image: ${imagePath}`);
}

async function pasteInEditor(session: ChromeSession): Promise<void> {
  const modifiers = process.platform === 'darwin' ? 4 : 2;
  await session.cdp.send('Input.dispatchKeyEvent', { type: 'keyDown', key: 'v', code: 'KeyV', modifiers, windowsVirtualKeyCode: 86 }, { sessionId: session.sessionId });
  await sleep(50);
  await session.cdp.send('Input.dispatchKeyEvent', { type: 'keyUp', key: 'v', code: 'KeyV', modifiers, windowsVirtualKeyCode: 86 }, { sessionId: session.sessionId });
}

async function sendCopy(cdp?: CdpConnection, sessionId?: string): Promise<void> {
  if (process.platform === 'darwin') {
    spawnSync('osascript', ['-e', 'tell application "System Events" to keystroke "c" using command down']);
  } else if (process.platform === 'linux') {
    spawnSync('xdotool', ['key', 'ctrl+c']);
  } else if (cdp && sessionId) {
    await cdp.send('Input.dispatchKeyEvent', { type: 'keyDown', key: 'c', code: 'KeyC', modifiers: 2, windowsVirtualKeyCode: 67 }, { sessionId });
    await sleep(50);
    await cdp.send('Input.dispatchKeyEvent', { type: 'keyUp', key: 'c', code: 'KeyC', modifiers: 2, windowsVirtualKeyCode: 67 }, { sessionId });
  }
}

async function sendPaste(cdp?: CdpConnection, sessionId?: string): Promise<void> {
  if (process.platform === 'darwin') {
    spawnSync('osascript', ['-e', 'tell application "System Events" to keystroke "v" using command down']);
  } else if (process.platform === 'linux') {
    spawnSync('xdotool', ['key', 'ctrl+v']);
  } else if (cdp && sessionId) {
    await cdp.send('Input.dispatchKeyEvent', { type: 'keyDown', key: 'v', code: 'KeyV', modifiers: 2, windowsVirtualKeyCode: 86 }, { sessionId });
    await sleep(50);
    await cdp.send('Input.dispatchKeyEvent', { type: 'keyUp', key: 'v', code: 'KeyV', modifiers: 2, windowsVirtualKeyCode: 86 }, { sessionId });
  }
}

async function copyHtmlFromBrowser(cdp: CdpConnection, htmlFilePath: string, contentImages: ImageInfo[] = []): Promise<void> {
  const absolutePath = path.isAbsolute(htmlFilePath) ? htmlFilePath : path.resolve(process.cwd(), htmlFilePath);
  const fileUrl = `file://${absolutePath}`;

  console.log(`[wechat] Opening HTML file in new tab: ${fileUrl}`);

  const { targetId } = await cdp.send<{ targetId: string }>('Target.createTarget', { url: fileUrl });
  const { sessionId } = await cdp.send<{ sessionId: string }>('Target.attachToTarget', { targetId, flatten: true });

  await cdp.send('Page.enable', {}, { sessionId });
  await cdp.send('Runtime.enable', {}, { sessionId });
  await sleep(2000);

  if (contentImages.length > 0) {
    console.log('[wechat] Replacing img tags with placeholders for browser paste...');
    const replacements = contentImages.map(img => ({ placeholder: img.placeholder, localPath: img.localPath }));
    await cdp.send<{ result: { value: unknown } }>('Runtime.evaluate', {
      expression: `
        (function() {
          const replacements = ${JSON.stringify(replacements)};
          for (const r of replacements) {
            const imgs = document.querySelectorAll('img[src="' + r.placeholder + '"], img[data-local-path="' + r.localPath + '"]');
            for (const img of imgs) {
              const text = document.createTextNode(r.placeholder);
              img.parentNode.replaceChild(text, img);
            }
          }
          return true;
        })()
      `,
      returnByValue: true,
    }, { sessionId });
    await sleep(500);
  }

  console.log('[wechat] Selecting #output content...');
  await cdp.send<{ result: { value: unknown } }>('Runtime.evaluate', {
    expression: `
      (function() {
        const output = document.querySelector('#output') || document.body;
        const range = document.createRange();
        range.selectNodeContents(output);
        const selection = window.getSelection();
        selection.removeAllRanges();
        selection.addRange(range);
        return true;
      })()
    `,
    returnByValue: true,
  }, { sessionId });
  await sleep(300);

  console.log('[wechat] Copying content...');
  await sendCopy(cdp, sessionId);
  await sleep(1000);

  console.log('[wechat] Closing HTML tab...');
  await cdp.send('Target.closeTarget', { targetId });
}

async function pasteFromClipboardInEditor(session: ChromeSession): Promise<void> {
  console.log('[wechat] Pasting content...');
  await sendPaste(session.cdp, session.sessionId);
  await sleep(1000);
}

async function editorHasSubstantiveContent(session: ChromeSession): Promise<boolean> {
  return await evaluate<boolean>(session, `
    (function() {
      const editor = document.querySelector('.ProseMirror');
      if (!editor) return false;
      const text = (editor.innerText || '').replace(/\\s+/g, '').trim();
      const html = (editor.innerHTML || '')
        .replace(/<p><br class="ProseMirror-trailingBreak"><\\/p>/g, '')
        .replace(/&nbsp;/g, '')
        .trim();
      const hasImage = !!editor.querySelector('img');
      return text.length > 20 || hasImage || html.length > 40;
    })()
  `);
}

async function pasteHtmlIntoEditorWithRetry(
  cdp: CdpConnection,
  session: ChromeSession,
  htmlFilePath: string,
  contentImages: ImageInfo[],
  maxAttempts = 3,
): Promise<boolean> {
  for (let attempt = 1; attempt <= maxAttempts; attempt++) {
    console.log(`[wechat] Copying HTML content from: ${htmlFilePath} (attempt ${attempt}/${maxAttempts})`);
    await copyHtmlFromBrowser(cdp, htmlFilePath, contentImages);
    await sleep(500);
    await clickElement(session, '.ProseMirror');
    await sleep(400);
    console.log('[wechat] Pasting into editor...');
    await pasteFromClipboardInEditor(session);
    await sleep(3000);

    const ok = await editorHasSubstantiveContent(session);
    if (ok) {
      console.log('[wechat] Body content verified OK.');
      return true;
    }

    console.warn(`[wechat] Body content verification failed after attempt ${attempt}.`);
    await sleep(1200);
  }
  return false;
}

function parseFrontmatter(content: string): Record<string, string> {
  const match = content.match(/^---\r?\n([\s\S]*?)\r?\n---\r?\n/);
  if (!match) return {};

  const frontmatter: Record<string, string> = {};
  for (const line of match[1]!.split('\n')) {
    const colonIdx = line.indexOf(':');
    if (colonIdx <= 0) continue;
    const key = line.slice(0, colonIdx).trim();
    let value = line.slice(colonIdx + 1).trim();
    if ((value.startsWith('"') && value.endsWith('"')) || (value.startsWith("'") && value.endsWith("'"))) {
      value = value.slice(1, -1);
    }
    frontmatter[key] = value;
  }
  return frontmatter;
}

function loadFrontmatterFromMarkdown(markdownPath: string): Record<string, string> {
  if (!fs.existsSync(markdownPath)) return {};
  return parseFrontmatter(fs.readFileSync(markdownPath, 'utf-8'));
}

function stripHtmlToText(input: string): string {
  return input
    .replace(/<br\s*\/?>/gi, '\n')
    .replace(/<\/p>/gi, '\n')
    .replace(/<[^>]+>/g, ' ')
    .replace(/&nbsp;/g, ' ')
    .replace(/&amp;/g, '&')
    .replace(/&lt;/g, '<')
    .replace(/&gt;/g, '>')
    .replace(/\s+/g, ' ')
    .trim();
}

function isGenericHtmlTitle(title: string): boolean {
  const normalized = title.trim().toLowerCase();
  return !normalized ||
    normalized === '微信公众号文章' ||
    normalized === 'wechat article' ||
    normalized === 'untitled';
}

function parseHtmlMeta(htmlPath: string): { title: string; author: string; summary: string; contentImages: ImageInfo[] } {
  const content = fs.readFileSync(htmlPath, 'utf-8');
  const baseDir = path.dirname(htmlPath);

  let title = '';
  const titleMatch = content.match(/<title>([^<]+)<\/title>/i);
  if (titleMatch) title = stripHtmlToText(titleMatch[1]!);

  if (isGenericHtmlTitle(title)) {
    const headingMatch = content.match(/<h1[^>]*>([\s\S]*?)<\/h1>/i)
      || content.match(/<h2[^>]*>([\s\S]*?)<\/h2>/i);
    if (headingMatch) {
      const headingText = stripHtmlToText(headingMatch[1]!);
      if (headingText) title = headingText;
    }
  }

  let author = '';
  const authorMatch = content.match(/<meta\s+name=["']author["']\s+content=["']([^"']+)["']/i)
    || content.match(/<meta\s+content=["']([^"']+)["']\s+name=["']author["']/i);
  if (authorMatch) author = authorMatch[1]!;

  let summary = '';
  const descMatch = content.match(/<meta\s+name=["']description["']\s+content=["']([^"']+)["']/i)
    || content.match(/<meta\s+content=["']([^"']+)["']\s+name=["']description["']/i);
  if (descMatch) summary = descMatch[1]!;

  if (!summary) {
    const paragraphMatches = content.matchAll(/<p[^>]*>([\s\S]*?)<\/p>/gi);
    for (const match of paragraphMatches) {
      const text = stripHtmlToText(match[1]!);
      if (text.length > 20) {
        summary = text.length > 120 ? text.slice(0, 117) + '...' : text;
        break;
      }
    }
  }

  const mdPath = htmlPath.replace(/\.html$/i, '.md');
  if (fs.existsSync(mdPath)) {
    const mdContent = fs.readFileSync(mdPath, 'utf-8');
    const fmMatch = mdContent.match(/^---\r?\n([\s\S]*?)\r?\n---/);
    if (fmMatch) {
      const lines = fmMatch[1]!.split('\n');
      for (const line of lines) {
        const colonIdx = line.indexOf(':');
        if (colonIdx > 0) {
          const key = line.slice(0, colonIdx).trim();
          let value = line.slice(colonIdx + 1).trim();
          if ((value.startsWith('"') && value.endsWith('"')) || (value.startsWith("'") && value.endsWith("'"))) {
            value = value.slice(1, -1);
          }
          if (key === 'title' && !title) title = value;
          if (key === 'author' && !author) author = value;
          if ((key === 'description' || key === 'summary') && !summary) summary = value;
        }
      }
    }
  }

  const contentImages: ImageInfo[] = [];
  const imgRegex = /<img[^>]*\ssrc=["']([^"']+)["'][^>]*>/gi;
  const matches = [...content.matchAll(imgRegex)];
  for (const match of matches) {
    const [fullTag, src] = match;
    if (!src || src.startsWith('http') || src.startsWith('data:') || src.startsWith('blob:')) continue;
    const localPathMatch = fullTag.match(/data-local-path=["']([^"']+)["']/);
    const localPath = localPathMatch?.[1]
      ? path.resolve(localPathMatch[1]!)
      : path.resolve(baseDir, src);
    if (!fs.existsSync(localPath)) continue;

    if (localPathMatch) {
      contentImages.push({
        placeholder: src,
        localPath,
        originalPath: src,
      });
      continue;
    }

    contentImages.push({
      placeholder: src,
      localPath,
      originalPath: src,
    });
  }

  return { title, author, summary, contentImages };
}

function resolveExistingPath(baseDir: string, value?: string): string | undefined {
  if (!value) return undefined;
  const resolved = path.isAbsolute(value) ? value : path.resolve(baseDir, value);
  return fs.existsSync(resolved) ? resolved : undefined;
}

function resolveCoverPath(options: {
  explicitCoverPath?: string;
  markdownFile?: string;
  htmlFile?: string;
  contentImages: ImageInfo[];
}): string | undefined {
  const { explicitCoverPath, markdownFile, htmlFile, contentImages } = options;
  const sourceFile = markdownFile || htmlFile;
  const baseDir = sourceFile ? path.dirname(sourceFile) : process.cwd();

  const candidates: Array<string | undefined> = [];
  candidates.push(resolveExistingPath(process.cwd(), explicitCoverPath));

  let frontmatter: Record<string, string> = {};
  if (markdownFile) {
    frontmatter = loadFrontmatterFromMarkdown(markdownFile);
  } else if (htmlFile) {
    const mdPath = htmlFile.replace(/\.html$/i, '.md');
    if (fs.existsSync(mdPath)) {
      frontmatter = loadFrontmatterFromMarkdown(mdPath);
    }
  }

  candidates.push(resolveExistingPath(baseDir, frontmatter.coverImage));
  candidates.push(resolveExistingPath(baseDir, frontmatter.featureImage));
  candidates.push(resolveExistingPath(baseDir, frontmatter.cover));
  candidates.push(resolveExistingPath(baseDir, frontmatter.image));
  candidates.push(resolveExistingPath(baseDir, 'imgs/cover.svg'));
  candidates.push(resolveExistingPath(baseDir, 'imgs/cover.png'));
  candidates.push(resolveExistingPath(baseDir, 'images/cover-wide.svg'));
  candidates.push(resolveExistingPath(baseDir, 'images/cover-wide.png'));
  candidates.push(resolveExistingPath(baseDir, 'images/cover.svg'));
  candidates.push(resolveExistingPath(baseDir, 'images/cover.png'));
  candidates.push(resolveExistingPath(baseDir, 'cover.svg'));
  candidates.push(resolveExistingPath(baseDir, 'cover.png'));

  if (contentImages.length > 0 && fs.existsSync(contentImages[0]!.localPath)) {
    candidates.push(contentImages[0]!.localPath);
  }

  return prepareWechatCoverPath(candidates.find(Boolean), {
    size: '900x383',
    logPrefix: '[wechat]',
  });
}

async function setFileInputFiles(session: ChromeSession, selector: string, files: string[]): Promise<void> {
  const root = await session.cdp.send<{ root: { nodeId: number } }>('DOM.getDocument', {}, { sessionId: session.sessionId });
  const query = await session.cdp.send<{ nodeId: number }>('DOM.querySelector', {
    nodeId: root.root.nodeId,
    selector,
  }, { sessionId: session.sessionId });

  if (!query.nodeId) {
    throw new Error(`File input not found: ${selector}`);
  }

  await session.cdp.send('DOM.setFileInputFiles', {
    nodeId: query.nodeId,
    files,
  }, { sessionId: session.sessionId });
}

async function querySelectorAllNodeIds(session: ChromeSession, selector: string): Promise<number[]> {
  const root = await session.cdp.send<{ root: { nodeId: number } }>('DOM.getDocument', {}, { sessionId: session.sessionId });
  const query = await session.cdp.send<{ nodeIds: number[] }>('DOM.querySelectorAll', {
    nodeId: root.root.nodeId,
    selector,
  }, { sessionId: session.sessionId });
  return query.nodeIds || [];
}

function getCoverReadyExpression(): string {
  return `
    (function() {
      const area = document.querySelector('#js_cover_area');
      if (!area) return false;

      const candidates = [
        area.querySelector('.js_cover_preview_new'),
        area.querySelector('.weui-desktop-publish__cover__thumb'),
        area.querySelector('.weui-desktop-publish__cover-item .weui-desktop-publish__cover__thumb'),
      ].filter(Boolean);

      for (const node of candidates) {
        const bg = getComputedStyle(node).backgroundImage || '';
        if (bg && bg !== 'none' && !/url\\((["'])?\\s*(data:)?\\s*\\1?\\)/.test(bg)) {
          return true;
        }
        const img = node.querySelector('img');
        if (img && img.getAttribute('src')) {
          return true;
        }
      }

      return false;
    })()
  `.trim();
}

async function setCoverFileInput(session: ChromeSession, absoluteCoverPath: string): Promise<void> {
  const selectors = [
    '.weui-desktop-dialog__wrp input[type="file"][name="file"]',
    '.weui-desktop-dialog__wrp input[type="file"]',
    '#js_cover_area input[type="file"][name="file"]',
    '#js_cover_area input[type="file"]',
    'input[type="file"][name="file"]',
  ];

  for (const selector of selectors) {
    const nodeIds = await querySelectorAllNodeIds(session, selector);
    if (nodeIds.length === 0) continue;

    for (const nodeId of [...nodeIds].reverse()) {
      await session.cdp.send('DOM.setFileInputFiles', {
        nodeId,
        files: [absoluteCoverPath],
      }, { sessionId: session.sessionId });

      const changed = await waitForCondition(session, `
        (function() {
          const dialogs = Array.from(document.querySelectorAll('.weui-desktop-dialog__wrp'));
          const hasVisibleDialog = dialogs.some(el => getComputedStyle(el).display !== 'none');
          if (hasVisibleDialog) return true;
          return ${getCoverReadyExpression()};
        })()
      `, 4_000);

      if (changed) return;
      await sleep(400);
    }
  }

  throw new Error('Cover file input not found or did not react to upload.');
}

async function waitForCondition(session: ChromeSession, expression: string, timeoutMs = 15_000): Promise<boolean> {
  const start = Date.now();
  while (Date.now() - start < timeoutMs) {
    const ok = await evaluate<boolean>(session, expression);
    if (ok) return true;
    await sleep(500);
  }
  return false;
}

async function clickVisibleDialogPrimaryButton(session: ChromeSession): Promise<boolean> {
  return await evaluate<boolean>(session, `
    (function() {
      const wrappers = Array.from(document.querySelectorAll('.weui-desktop-dialog__wrp'));
      const visible = wrappers.find(el => getComputedStyle(el).display !== 'none');
      if (!visible) return false;

      const buttons = Array.from(visible.querySelectorAll('button, a, .weui-desktop-btn'))
        .filter(btn => {
          const style = getComputedStyle(btn);
          if (style.display === 'none' || style.visibility === 'hidden') return false;
          if ((btn.offsetWidth || 0) === 0 && (btn.offsetHeight || 0) === 0) return false;
          return true;
        });
      const textMatch = ['确定', '完成', '确认', '使用', '保存', '下一步'];
      for (const btn of buttons) {
        const text = (btn.textContent || '').trim();
        if (textMatch.some(word => text.includes(word))) {
          btn.dispatchEvent(new MouseEvent('click', { bubbles: true }));
          return true;
        }
      }

      const primary = visible.querySelector('.weui-desktop-btn_primary, .btn_primary, .weui-desktop-btn_main');
      if (primary) {
        primary.dispatchEvent(new MouseEvent('click', { bubbles: true }));
        return true;
      }

      return false;
    })()
  `);
}

async function clickVisibleDialogButtonByText(session: ChromeSession, labels: string[]): Promise<boolean> {
  return await evaluate<boolean>(session, `
    (function() {
      const wrappers = Array.from(document.querySelectorAll('.weui-desktop-dialog__wrp'));
      const visible = wrappers.find(el => getComputedStyle(el).display !== 'none');
      if (!visible) return false;

      const buttons = Array.from(visible.querySelectorAll('button, a, .weui-desktop-btn'))
        .filter(btn => {
          const style = getComputedStyle(btn);
          if (style.display === 'none' || style.visibility === 'hidden') return false;
          if ((btn.offsetWidth || 0) === 0 && (btn.offsetHeight || 0) === 0) return false;
          return true;
        });
      const labels = ${JSON.stringify(labels)};
      for (const label of labels) {
        const target = buttons.find(btn => (btn.textContent || '').trim().includes(label));
        if (target) {
          target.dispatchEvent(new MouseEvent('click', { bubbles: true }));
          return true;
        }
      }
      return false;
    })()
  `);
}

async function resolveCoverDialogs(session: ChromeSession): Promise<void> {
  for (let i = 0; i < 4; i++) {
    const dialogVisible = await evaluate<boolean>(session, `
      Array.from(document.querySelectorAll('.weui-desktop-dialog__wrp'))
        .some(el => getComputedStyle(el).display !== 'none')
    `);
    if (!dialogVisible) return;

    const clicked = await clickVisibleDialogPrimaryButton(session);
    if (!clicked) return;
    await sleep(2500);
  }
}

async function openCoverChooser(session: ChromeSession): Promise<void> {
  await clickElement(session, '#js_cover_area .js_cover_btn_area');
  const opened = await waitForCondition(session, `
    (function() {
      const chooser = document.querySelector('#js_cover_area #js_cover_null');
      return !!chooser && getComputedStyle(chooser).display !== 'none';
    })()
  `, 3_000);
  if (!opened) {
    throw new Error('Cover chooser did not open.');
  }
}

async function selectCoverFromContent(session: ChromeSession, coverIndex: number): Promise<boolean> {
  console.log(`[wechat] Selecting cover from article content at index ${coverIndex + 1}...`);
  await openCoverChooser(session);

  const sourceClicked = await evaluate<boolean>(session, `
    (function() {
      const btn = document.querySelector('#js_cover_area .js_selectCoverFromContent');
      if (!btn) return false;
      btn.dispatchEvent(new MouseEvent('click', { bubbles: true }));
      return true;
    })()
  `);
  if (!sourceClicked) {
    throw new Error('Could not open "select cover from content" flow.');
  }

  const pickerVisible = await waitForCondition(session, `
    Array.from(document.querySelectorAll('.weui-desktop-dialog__wrp'))
      .some(el => getComputedStyle(el).display !== 'none' && (el.textContent || '').includes('选择图片'))
  `, 8_000);
  if (!pickerVisible) {
    const debug = await evaluate<string>(session, `
      JSON.stringify(
        Array.from(document.querySelectorAll('body *'))
          .filter(el => {
            const text = (el.textContent || '').trim();
            const cls = el.className || '';
            return text.includes('从正文选择')
              || text.includes('选择图片')
              || text.includes('编辑封面')
              || text.includes('封面')
              || String(cls).includes('cover')
              || String(cls).includes('img');
          })
          .slice(0, 40)
          .map(el => ({
            tag: el.tagName,
            cls: String(el.className || ''),
            text: (el.textContent || '').trim().slice(0, 120)
          }))
      )
    `);
    console.log(`[wechat] Cover picker debug: ${debug}`);
    throw new Error('Content image picker did not open.');
  }

  const pickerInfo = await evaluate<string>(session, `
    JSON.stringify(
      Array.from(document.querySelectorAll('.weui-desktop-dialog__wrp'))
        .filter(el => getComputedStyle(el).display !== 'none' && (el.textContent || '').includes('选择图片'))
        .map(el => ({
          text: (el.textContent || '').trim().slice(0, 300),
          itemCount: el.querySelectorAll('.appmsg_content_img_item').length,
          html: el.outerHTML.slice(0, 2000)
        }))
    )
  `);
  console.log(`[wechat] Cover picker visible: ${pickerInfo}`);

  const selected = await evaluate<boolean>(session, `
    (function() {
      const wrappers = Array.from(document.querySelectorAll('.weui-desktop-dialog__wrp'));
      const visible = wrappers.find(el => getComputedStyle(el).display !== 'none' && (el.textContent || '').includes('选择图片'));
      if (!visible) return false;
      const items = Array.from(visible.querySelectorAll('.appmsg_content_img_item'));
      const target = items[${coverIndex}] || items[0];
      if (!target) return false;
      target.dispatchEvent(new MouseEvent('click', { bubbles: true }));
      return true;
    })()
  `);
  if (!selected) {
    throw new Error('Could not select a content image as cover.');
  }
  await sleep(500);

  const selectedState = await evaluate<string>(session, `
    JSON.stringify(
      Array.from(document.querySelectorAll('.weui-desktop-dialog__wrp'))
        .filter(el => getComputedStyle(el).display !== 'none' && (el.textContent || '').includes('选择图片'))
        .map(el => ({
          selectedCount: el.querySelectorAll('.appmsg_content_img_item.selected, .appmsg_content_img_item.actived, .appmsg_content_img_item.active').length,
          html: el.outerHTML.slice(0, 2000)
        }))
    )
  `);
  console.log(`[wechat] Cover picker selected state: ${selectedState}`);

  const advanced = await clickVisibleDialogButtonByText(session, ['完成', '下一步']);
  if (!advanced) {
    throw new Error('Could not advance from content image picker.');
  }

  const cropVisible = await waitForCondition(session, `
    Array.from(document.querySelectorAll('.weui-desktop-dialog__wrp'))
      .some(el => {
        if (getComputedStyle(el).display === 'none') return false;
        if (!(el.textContent || '').includes('编辑封面')) return false;
        const buttons = Array.from(el.querySelectorAll('button, a, .weui-desktop-btn'));
        return buttons.some(btn => {
          const text = (btn.textContent || '').trim();
          const style = getComputedStyle(btn);
          return (text.includes('确认') || text.includes('完成'))
            && style.display !== 'none'
            && style.visibility !== 'hidden'
            && ((btn.offsetWidth || 0) > 0 || (btn.offsetHeight || 0) > 0);
        });
      })
  `, 12_000);
  if (!cropVisible) {
    throw new Error('Cover crop dialog did not appear.');
  }

  const cropInfo = await evaluate<string>(session, `
    JSON.stringify(
      Array.from(document.querySelectorAll('.weui-desktop-dialog__wrp'))
        .filter(el => getComputedStyle(el).display !== 'none' && (el.textContent || '').includes('编辑封面'))
        .map(el => ({
          text: (el.textContent || '').trim().slice(0, 300),
          html: el.outerHTML.slice(0, 2000)
        }))
    )
  `);
  console.log(`[wechat] Cover crop dialog: ${cropInfo}`);

  const confirmed = await clickVisibleDialogButtonByText(session, ['确认', '完成']);
  if (!confirmed) {
    throw new Error('Could not confirm cover crop.');
  }
  await sleep(3_000);

  return await waitForCondition(session, getCoverReadyExpression(), 20_000);
}

async function uploadCoverImage(session: ChromeSession, coverPath: string, contentImages: ImageInfo[] = []): Promise<boolean> {
  const absoluteCoverPath = path.resolve(coverPath);
  if (!fs.existsSync(absoluteCoverPath)) {
    throw new Error(`Cover image not found: ${absoluteCoverPath}`);
  }

  console.log(`[wechat] Uploading cover: ${absoluteCoverPath}`);
  await waitForElement(session, '#js_cover_area', 20_000);

  const matchedContentIndex = contentImages.findIndex((img) => {
    try {
      return path.resolve(img.localPath) === absoluteCoverPath;
    } catch {
      return false;
    }
  });
  if (matchedContentIndex >= 0) {
    const selected = await selectCoverFromContent(session, matchedContentIndex);
    if (selected) {
      console.log('[wechat] Cover selected from article content.');
      return true;
    }
  }

  try {
    await clickElement(session, '#js_cover_area .js_cover_btn_area');
    await sleep(400);
  } catch {}

  try {
    await setCoverFileInput(session, absoluteCoverPath);
    await sleep(1000);
    await resolveCoverDialogs(session);
  } catch (error) {
    console.warn('[wechat] Cover file input path failed, trying clipboard paste fallback.');
    await copyImageToClipboard(absoluteCoverPath);
    try {
      await clickElement(session, '#js_cover_area .js_cover_btn_area');
    } catch {
      try {
        await clickElement(session, '#js_cover_area');
      } catch {}
    }
    await sleep(500);
    await pasteInEditor(session);
    await sleep(1000);
    await resolveCoverDialogs(session);
  }

  const uploaded = await waitForCondition(session, getCoverReadyExpression(), 20_000);

  if (uploaded) {
    console.log('[wechat] Cover uploaded successfully.');
  } else {
    console.warn('[wechat] Cover upload did not reach a confirmed preview state.');
  }

  return uploaded;
}

async function selectAndReplacePlaceholder(session: ChromeSession, placeholder: string): Promise<boolean> {
  for (let attempt = 1; attempt <= 5; attempt++) {
    const result = await session.cdp.send<{ result: { value: boolean } }>('Runtime.evaluate', {
      expression: `
        (function() {
          const editor = document.querySelector('.ProseMirror');
          if (!editor) return false;

          const placeholder = ${JSON.stringify(placeholder)};
          const walker = document.createTreeWalker(editor, NodeFilter.SHOW_TEXT, null, false);
          let node;

          while ((node = walker.nextNode())) {
            const text = node.textContent || '';
            let searchStart = 0;
            let idx;
            // Search for exact match (not prefix of longer placeholder like XIMGPH_1 in XIMGPH_10)
            while ((idx = text.indexOf(placeholder, searchStart)) !== -1) {
              const afterIdx = idx + placeholder.length;
              const charAfter = text[afterIdx];
              // Exact match if next char is not a digit
              if (charAfter === undefined || !/\\d/.test(charAfter)) {
                node.parentElement.scrollIntoView({ behavior: 'smooth', block: 'center' });

                const range = document.createRange();
                range.setStart(node, idx);
                range.setEnd(node, idx + placeholder.length);
                const sel = window.getSelection();
                sel.removeAllRanges();
                sel.addRange(range);
                return true;
              }
              searchStart = afterIdx;
            }
          }
          return false;
        })()
      `,
      returnByValue: true,
    }, { sessionId: session.sessionId });

    if (result.result.value) {
      return true;
    }

    await sleep(800);
  }

  return false;
}

async function pressDeleteKey(session: ChromeSession): Promise<void> {
  await session.cdp.send('Input.dispatchKeyEvent', { type: 'keyDown', key: 'Backspace', code: 'Backspace', windowsVirtualKeyCode: 8 }, { sessionId: session.sessionId });
  await sleep(50);
  await session.cdp.send('Input.dispatchKeyEvent', { type: 'keyUp', key: 'Backspace', code: 'Backspace', windowsVirtualKeyCode: 8 }, { sessionId: session.sessionId });
}

async function removeExtraEmptyLineAfterImage(session: ChromeSession): Promise<boolean> {
  const removed = await evaluate<boolean>(session, `
    (function() {
      const editor = document.querySelector('.ProseMirror');
      if (!editor) return false;

      const sel = window.getSelection();
      if (!sel || sel.rangeCount === 0) return false;

      let node = sel.anchorNode;
      if (!node) return false;
      let element = node.nodeType === Node.ELEMENT_NODE ? node : node.parentElement;
      if (!element || !editor.contains(element)) return false;

      const isEmptyParagraph = (el) => {
        if (!el || el.tagName !== 'P') return false;
        const text = (el.textContent || '').trim();
        if (text.length > 0) return false;
        return el.querySelectorAll('img, figure, video, iframe').length === 0;
      };

      const hasImage = (el) => {
        if (!el) return false;
        return !!el.querySelector('img, figure img, picture img');
      };

      const placeCursorAfter = (el) => {
        if (!el) return;
        const range = document.createRange();
        range.setStartAfter(el);
        range.collapse(true);
        sel.removeAllRanges();
        sel.addRange(range);
      };

      // Case 1: caret is inside an empty paragraph right after an image block.
      const emptyPara = element.closest('p');
      if (emptyPara && editor.contains(emptyPara) && isEmptyParagraph(emptyPara)) {
        const prev = emptyPara.previousElementSibling;
        if (prev && hasImage(prev)) {
          emptyPara.remove();
          placeCursorAfter(prev);
          return true;
        }
      }

      // Case 2: caret is on the image block itself; remove the next empty paragraph.
      const imageBlock = element.closest('figure, p');
      if (imageBlock && editor.contains(imageBlock) && hasImage(imageBlock)) {
        const next = imageBlock.nextElementSibling;
        if (next && isEmptyParagraph(next)) {
          next.remove();
          placeCursorAfter(imageBlock);
          return true;
        }
      }

      return false;
    })()
  `);

  if (removed) console.log('[wechat] Removed extra empty line after image.');
  return removed;
}

async function placeCursorAtEndOfEditor(session: ChromeSession): Promise<void> {
  await evaluate(session, `
    (function() {
      const editor = document.querySelector('.ProseMirror');
      if (!editor) return false;
      editor.focus();
      const range = document.createRange();
      range.selectNodeContents(editor);
      range.collapse(false);
      const sel = window.getSelection();
      sel.removeAllRanges();
      sel.addRange(range);
      return true;
    })()
  `);
  await sleep(200);
}

export async function postArticle(options: ArticleOptions): Promise<void> {
  const { title, content, htmlFile, markdownFile, coverPath, theme, color, author, summary, images = [], submit = false, profileDir, cdpPort } = options;
  let { contentImages = [] } = options;
  let effectiveTitle = title || '';
  let effectiveAuthor = author || '';
  let effectiveSummary = summary || '';
  let effectiveHtmlFile = htmlFile;

  if (markdownFile) {
    console.log(`[wechat] Parsing markdown: ${markdownFile}`);
    const formattedHtmlPath = renderMarkdownWithPreferredFormatter(markdownFile, {
      theme: normalizePreferredFormatterTheme(theme, '[wechat]'),
      outputPath: markdownFile.replace(/\.md$/i, '.wechat-publisher.html'),
      logPrefix: '[wechat]',
    });
    const meta = parseHtmlMeta(formattedHtmlPath);
    effectiveTitle = effectiveTitle || meta.title;
    effectiveAuthor = effectiveAuthor || meta.author;
    effectiveSummary = effectiveSummary || meta.summary;
    effectiveHtmlFile = formattedHtmlPath;
    contentImages = meta.contentImages;
    console.log(`[wechat] Title: ${effectiveTitle || '(empty)'}`);
    console.log(`[wechat] Author: ${effectiveAuthor || '(empty)'}`);
    console.log(`[wechat] Summary: ${effectiveSummary || '(empty)'}`);
    console.log(`[wechat] Found ${contentImages.length} images to insert`);
  } else if (htmlFile && fs.existsSync(htmlFile)) {
    console.log(`[wechat] Parsing HTML: ${htmlFile}`);
    const meta = parseHtmlMeta(htmlFile);
    effectiveTitle = effectiveTitle || meta.title;
    effectiveAuthor = effectiveAuthor || meta.author;
    effectiveSummary = effectiveSummary || meta.summary;
    effectiveHtmlFile = htmlFile;
    if (meta.contentImages.length > 0) {
      contentImages = meta.contentImages;
    }
    console.log(`[wechat] Title: ${effectiveTitle || '(empty)'}`);
    console.log(`[wechat] Author: ${effectiveAuthor || '(empty)'}`);
    console.log(`[wechat] Summary: ${effectiveSummary || '(empty)'}`);
    console.log(`[wechat] Found ${contentImages.length} images to insert`);
  }

  const effectiveCoverPath = resolveCoverPath({
    explicitCoverPath: coverPath,
    markdownFile,
    htmlFile,
    contentImages,
  });
  if (effectiveCoverPath) {
    console.log(`[wechat] Cover candidate: ${effectiveCoverPath}`);
  } else {
    console.warn('[wechat] No cover candidate found. Draft card may show placeholder background.');
  }

  if (effectiveTitle && effectiveTitle.length > 64) throw new Error(`Title too long: ${effectiveTitle.length} chars (max 64)`);
  if (!content && !effectiveHtmlFile) throw new Error('Either --content, --html, or --markdown is required');

  let cdp: CdpConnection;
  let chrome: ReturnType<typeof import('node:child_process').spawn> | null = null;

  // Try connecting to existing Chrome: explicit port > auto-detect > launch new
  const portToTry = cdpPort ?? await findExistingChromeDebugPort();
  if (portToTry) {
    const existing = await tryConnectExisting(portToTry);
    if (existing) {
      console.log(`[cdp] Connected to existing Chrome on port ${portToTry}`);
      cdp = existing;
    } else {
      console.log(`[cdp] Port ${portToTry} not available, launching new Chrome...`);
      const launched = await launchChrome(WECHAT_URL, profileDir);
      cdp = launched.cdp;
      chrome = launched.chrome;
    }
  } else {
    const launched = await launchChrome(WECHAT_URL, profileDir);
    cdp = launched.cdp;
    chrome = launched.chrome;
  }

  try {
    console.log('[wechat] Waiting for page load...');
    await sleep(3000);

    let session: ChromeSession;
    if (!chrome) {
      // Reusing existing Chrome: find an already-logged-in tab (has token in URL)
      const allTargets = await cdp.send<{ targetInfos: Array<{ targetId: string; url: string; type: string }> }>('Target.getTargets');
      const loggedInTab = allTargets.targetInfos.find(t => t.type === 'page' && t.url.includes('mp.weixin.qq.com') && t.url.includes('token='));
      const wechatTab = loggedInTab || allTargets.targetInfos.find(t => t.type === 'page' && t.url.includes('mp.weixin.qq.com'));

      if (wechatTab) {
        console.log(`[wechat] Reusing existing tab: ${wechatTab.url.substring(0, 80)}...`);
        const { sessionId: reuseSid } = await cdp.send<{ sessionId: string }>('Target.attachToTarget', { targetId: wechatTab.targetId, flatten: true });
        await cdp.send('Page.enable', {}, { sessionId: reuseSid });
        await cdp.send('Runtime.enable', {}, { sessionId: reuseSid });
        await cdp.send('DOM.enable', {}, { sessionId: reuseSid });
        session = { cdp, sessionId: reuseSid, targetId: wechatTab.targetId };

        // If the reused tab is not already on home, open a fresh home tab instead of
        // mutating an editor tab that may have unsaved state or missing home UI.
        const currentUrl = await evaluate<string>(session, 'window.location.href');
        if (!currentUrl.includes('/cgi-bin/home')) {
          console.log('[wechat] Opening a fresh home tab...');
          const homeUrl = `${WECHAT_URL}cgi-bin/home?t=home/index`;
          const { targetId: homeTargetId } = await cdp.send<{ targetId: string }>('Target.createTarget', { url: homeUrl });
          const { sessionId: homeSid } = await cdp.send<{ sessionId: string }>('Target.attachToTarget', { targetId: homeTargetId, flatten: true });
          await cdp.send('Page.enable', {}, { sessionId: homeSid });
          await cdp.send('Runtime.enable', {}, { sessionId: homeSid });
          await cdp.send('DOM.enable', {}, { sessionId: homeSid });
          session = { cdp, sessionId: homeSid, targetId: homeTargetId };
          await sleep(5000);
        }
      } else {
        // No WeChat tab found, create one
        console.log('[wechat] No WeChat tab found, opening...');
        await cdp.send('Target.createTarget', { url: WECHAT_URL });
        await sleep(5000);
        session = await getPageSession(cdp, 'mp.weixin.qq.com');
      }
    } else {
      session = await getPageSession(cdp, 'mp.weixin.qq.com');
    }

    const url = await evaluate<string>(session, 'window.location.href');
    if (!url.includes('/cgi-bin/')) {
      console.log('[wechat] Not logged in. Please scan QR code...');
      const loggedIn = await waitForLogin(session);
      if (!loggedIn) throw new Error('Login timeout');
    }
    console.log('[wechat] Logged in.');
    await sleep(2000);

    // Wait for menu to be ready
    const menuReady = await waitForElement(session, '.new-creation__menu', 20_000);
    if (!menuReady) throw new Error('Home page menu did not load');

    const targets = await cdp.send<{ targetInfos: Array<{ targetId: string; url: string; type: string }> }>('Target.getTargets');
    const initialIds = new Set(targets.targetInfos.map(t => t.targetId));

    await clickMenuByText(session, '文章');
    await sleep(3000);

    const editorTargetId = await waitForNewTab(cdp, initialIds, 'mp.weixin.qq.com');
    console.log('[wechat] Editor tab opened.');

    const { sessionId } = await cdp.send<{ sessionId: string }>('Target.attachToTarget', { targetId: editorTargetId, flatten: true });
    session = { cdp, sessionId, targetId: editorTargetId };

    await cdp.send('Page.enable', {}, { sessionId });
    await cdp.send('Runtime.enable', {}, { sessionId });
    await cdp.send('DOM.enable', {}, { sessionId });

    await sleep(3000);

    if (effectiveTitle) {
      console.log('[wechat] Filling title...');
      await evaluate(session, `document.querySelector('#title').value = ${JSON.stringify(effectiveTitle)}; document.querySelector('#title').dispatchEvent(new Event('input', { bubbles: true }));`);
    }

    if (effectiveAuthor) {
      console.log('[wechat] Filling author...');
      await evaluate(session, `document.querySelector('#author').value = ${JSON.stringify(effectiveAuthor)}; document.querySelector('#author').dispatchEvent(new Event('input', { bubbles: true }));`);
    }

    await sleep(500);

    if (effectiveTitle) {
      const actualTitle = await evaluate<string>(session, `document.querySelector('#title')?.value || ''`);
      if (actualTitle === effectiveTitle) {
        console.log('[wechat] Title verified OK.');
      } else {
        console.warn(`[wechat] Title verification failed. Expected: "${effectiveTitle}", got: "${actualTitle}"`);
      }
    }

    const shouldDeferCoverSelection = Boolean(
      effectiveCoverPath &&
      contentImages.some((img) => path.resolve(img.localPath) === path.resolve(effectiveCoverPath))
    );

    if (effectiveCoverPath && !shouldDeferCoverSelection) {
      const uploaded = await uploadCoverImage(session, effectiveCoverPath, contentImages);
      if (!uploaded) {
        throw new Error('Cover upload failed: WeChat editor did not show a usable cover preview.');
      }
      await sleep(1000);
    }

    console.log('[wechat] Clicking on editor...');
    await clickElement(session, '.ProseMirror');
    await sleep(1000);

    console.log('[wechat] Ensuring editor focus...');
    await clickElement(session, '.ProseMirror');
    await sleep(500);

    if (effectiveHtmlFile && fs.existsSync(effectiveHtmlFile)) {
      const editorHasContent = await pasteHtmlIntoEditorWithRetry(cdp, session, effectiveHtmlFile, contentImages);
      if (!editorHasContent) {
        throw new Error('Editor remained empty after repeated paste attempts.');
      }

      if (contentImages.length > 0) {
        console.log(`[wechat] Inserting ${contentImages.length} images...`);
        await sleep(1200);
        for (let i = 0; i < contentImages.length; i++) {
          const img = contentImages[i]!;
          console.log(`[wechat] [${i + 1}/${contentImages.length}] Processing: ${img.placeholder}`);

          const found = await selectAndReplacePlaceholder(session, img.placeholder);
          if (!found) {
            console.warn(`[wechat] Placeholder not found: ${img.placeholder}`);
            console.log('[wechat] Falling back to appending image at end of article...');
            await placeCursorAtEndOfEditor(session);
            console.log(`[wechat] Copying image: ${path.basename(img.localPath)}`);
            await copyImageToClipboard(img.localPath);
            await sleep(300);
            console.log('[wechat] Pasting image at end...');
            await pasteFromClipboardInEditor(session);
            await sleep(3000);
            await removeExtraEmptyLineAfterImage(session);
            continue;
          }

          await sleep(500);

          console.log(`[wechat] Copying image: ${path.basename(img.localPath)}`);
          await copyImageToClipboard(img.localPath);
          await sleep(300);

          console.log('[wechat] Deleting placeholder with Backspace...');
          await pressDeleteKey(session);
          await sleep(200);

          console.log('[wechat] Pasting image...');
          await pasteFromClipboardInEditor(session);
          await sleep(3000);
          await removeExtraEmptyLineAfterImage(session);
        }
        console.log('[wechat] All images inserted.');
      }

      if (effectiveCoverPath && shouldDeferCoverSelection) {
        console.log('[wechat] Selecting cover after body images are inserted...');
        const uploaded = await uploadCoverImage(session, effectiveCoverPath, contentImages);
        if (!uploaded) {
          throw new Error('Cover upload failed after inserting body images.');
        }
        await sleep(1000);
      }
    } else if (content) {
      for (const img of images) {
        if (fs.existsSync(img)) {
          console.log(`[wechat] Pasting image: ${img}`);
          await copyImageToClipboard(img);
          await sleep(500);
          await pasteInEditor(session);
          await sleep(2000);
          await removeExtraEmptyLineAfterImage(session);
        }
      }

      console.log('[wechat] Typing content...');
      await typeText(session, content);
      await sleep(1000);

      const editorHasContent = await editorHasSubstantiveContent(session);
      if (editorHasContent) {
        console.log('[wechat] Body content verified OK.');
      } else {
        console.warn('[wechat] Body content verification failed: editor appears empty after typing.');
      }
    }

    if (effectiveSummary) {
      console.log(`[wechat] Filling summary (after content paste): ${effectiveSummary}`);
      await evaluate(session, `
        (function() {
          const el = document.querySelector('#js_description');
          if (!el) return;
          el.focus();
          el.select();
          el.value = ${JSON.stringify(effectiveSummary)};
          el.dispatchEvent(new Event('input', { bubbles: true }));
          el.dispatchEvent(new Event('change', { bubbles: true }));
          el.dispatchEvent(new Event('blur', { bubbles: true }));
        })()
      `);
      await sleep(500);

      const actualSummary = await evaluate<string>(session, `document.querySelector('#js_description')?.value || ''`);
      if (actualSummary === effectiveSummary) {
        console.log('[wechat] Summary verified OK.');
      } else {
        console.warn(`[wechat] Summary verification failed. Expected: "${effectiveSummary}", got: "${actualSummary}"`);
      }
    }

    console.log('[wechat] Saving as draft...');
    await evaluate(session, `document.querySelector('#js_submit button').click()`);
    await sleep(3000);

    const saved = await evaluate<boolean>(session, `!!document.querySelector('.weui-desktop-toast')`);
    if (saved) {
      console.log('[wechat] Draft saved successfully!');
    } else {
      console.log('[wechat] Waiting for save confirmation...');
      await sleep(5000);
    }

    console.log('[wechat] Done. Browser window left open.');
  } finally {
    cdp.close();
  }
}

function printUsage(): never {
  console.log(`Post article to WeChat Official Account

Usage:
  npx -y bun wechat-article.ts [options]

Options:
  --title <text>     Article title (auto-extracted from markdown)
  --content <text>   Article content (use with --image)
  --html <path>      HTML file to paste (alternative to --content)
  --markdown <path>  Markdown file to convert and post (preferred path uses repo-local formatter)
  --theme <name>     Theme for markdown (mist-blue default, ai-tech optional; legacy names auto-normalize)
  --color <name|hex> Legacy compatibility option; ignored by the repo-local formatter path
  --author <name>    Author name
  --summary <text>   Article summary
  --cover <path>     Cover image path (optional; accepts PNG/JPG/WEBP/SVG and falls back to imgs/cover.svg, imgs/cover.png, images/cover-wide.png, or first content image)
  --image <path>     Content image, can repeat (only with --content)
  --submit           Save as draft
  --profile <dir>    Chrome profile directory (defaults to wechat-publisher/EXTEND.md if set)
  --cdp-port <port>  Connect to existing Chrome debug port instead of launching new instance

Examples:
  npx -y bun wechat-article.ts --markdown article.md
  npx -y bun wechat-article.ts --markdown article.md --theme mist-blue --submit
  npx -y bun wechat-article.ts --markdown article.md --cover imgs/cover.svg --submit
  npx -y bun wechat-article.ts --title "标题" --content "内容" --image img.png
  npx -y bun wechat-article.ts --title "标题" --html article.html --submit

Markdown mode:
  Images in markdown are converted to placeholders. After pasting HTML,
  each placeholder is selected, scrolled into view, deleted, and replaced
  with the actual image via paste.
`);
  process.exit(0);
}

async function main(): Promise<void> {
  const args = process.argv.slice(2);
  if (args.includes('--help') || args.includes('-h')) printUsage();
  const extendConfig = loadExtendConfig();

  const images: string[] = [];
  let title: string | undefined;
  let content: string | undefined;
  let htmlFile: string | undefined;
  let markdownFile: string | undefined;
  let theme: string | undefined = extendConfig.defaultTheme;
  let color: string | undefined = extendConfig.defaultColor;
  let author: string | undefined = extendConfig.defaultAuthor;
  let summary: string | undefined;
  let coverPath: string | undefined;
  let submit = false;
  let profileDir: string | undefined = extendConfig.chromeProfilePath;
  let cdpPort: number | undefined;

  for (let i = 0; i < args.length; i++) {
    const arg = args[i]!;
    if (arg === '--title' && args[i + 1]) title = args[++i];
    else if (arg === '--content' && args[i + 1]) content = args[++i];
    else if (arg === '--html' && args[i + 1]) htmlFile = args[++i];
    else if (arg === '--markdown' && args[i + 1]) markdownFile = args[++i];
    else if (arg === '--theme' && args[i + 1]) theme = args[++i];
    else if (arg === '--color' && args[i + 1]) color = args[++i];
    else if (arg === '--author' && args[i + 1]) author = args[++i];
    else if (arg === '--summary' && args[i + 1]) summary = args[++i];
    else if (arg === '--cover' && args[i + 1]) coverPath = args[++i];
    else if (arg === '--image' && args[i + 1]) images.push(args[++i]!);
    else if (arg === '--submit') submit = true;
    else if (arg === '--profile' && args[i + 1]) profileDir = args[++i];
    else if (arg === '--cdp-port' && args[i + 1]) cdpPort = parseInt(args[++i]!, 10);
  }

  if (!markdownFile && !htmlFile && !title) { console.error('Error: --title is required (or use --markdown/--html)'); process.exit(1); }
  if (!markdownFile && !htmlFile && !content) { console.error('Error: --content, --html, or --markdown is required'); process.exit(1); }

  await postArticle({ title: title || '', content, htmlFile, markdownFile, coverPath, theme, color, author, summary, images, submit, profileDir, cdpPort });
}

await main().then(() => {
  process.exit(0);
}).catch((err) => {
  console.error(`Error: ${err instanceof Error ? err.message : String(err)}`);
  process.exit(1);
});
