import fs from "node:fs";
import path from "node:path";
import os from "node:os";
import { prepareWechatCoverPath } from "./cover-utils.ts";
import { normalizePreferredFormatterTheme, renderMarkdownWithPreferredFormatter } from "./preferred-markdown-render.ts";
import { loadWechatPublisherExtendConfig } from "./wechat-extend-config.ts";

interface WechatConfig {
  appId: string;
  appSecret: string;
}

interface ExtendConfig {
  defaultTheme?: string;
  defaultColor?: string;
  defaultAuthor?: string;
  needOpenComment?: boolean;
  onlyFansCanComment?: boolean;
}

interface AccessTokenResponse {
  access_token?: string;
  errcode?: number;
  errmsg?: string;
}

interface UploadResponse {
  media_id: string;
  url: string;
  errcode?: number;
  errmsg?: string;
}

interface PublishResponse {
  media_id?: string;
  errcode?: number;
  errmsg?: string;
}

interface DraftDeleteResponse {
  errcode?: number;
  errmsg?: string;
}

interface DraftNewsItem {
  title?: string;
}

interface DraftBatchItem {
  media_id: string;
  update_time?: number;
  content?: {
    news_item?: DraftNewsItem[];
  };
}

interface DraftBatchGetResponse {
  total_count?: number;
  item_count?: number;
  item?: DraftBatchItem[];
  errcode?: number;
  errmsg?: string;
}

type ArticleType = "news" | "newspic";
type CommandMode = "publish" | "draft-list" | "draft-delete" | "draft-delete-title";

interface ArticleOptions {
  title: string;
  author?: string;
  digest?: string;
  content: string;
  thumbMediaId: string;
  articleType: ArticleType;
  imageMediaIds?: string[];
  needOpenComment: boolean;
  onlyFansCanComment: boolean;
}

const TOKEN_URL = "https://api.weixin.qq.com/cgi-bin/token";
const UPLOAD_URL = "https://api.weixin.qq.com/cgi-bin/material/add_material";
const DRAFT_URL = "https://api.weixin.qq.com/cgi-bin/draft/add";
const DRAFT_BATCHGET_URL = "https://api.weixin.qq.com/cgi-bin/draft/batchget";
const DRAFT_DELETE_URL = "https://api.weixin.qq.com/cgi-bin/draft/delete";

function loadExtendConfig(): ExtendConfig {
  return loadWechatPublisherExtendConfig();
}

function loadEnvFile(envPath: string): Record<string, string> {
  const env: Record<string, string> = {};
  if (!fs.existsSync(envPath)) return env;

  const content = fs.readFileSync(envPath, "utf-8");
  for (const line of content.split("\n")) {
    const trimmed = line.trim();
    if (!trimmed || trimmed.startsWith("#")) continue;
    const eqIdx = trimmed.indexOf("=");
    if (eqIdx > 0) {
      const key = trimmed.slice(0, eqIdx).trim();
      let value = trimmed.slice(eqIdx + 1).trim();
      if ((value.startsWith('"') && value.endsWith('"')) ||
          (value.startsWith("'") && value.endsWith("'"))) {
        value = value.slice(1, -1);
      }
      env[key] = value;
    }
  }
  return env;
}

function loadConfig(): WechatConfig {
  const cwdEnvPath = path.join(process.cwd(), ".baoyu-skills", ".env");
  const homeEnvPath = path.join(os.homedir(), ".baoyu-skills", ".env");

  const cwdEnv = loadEnvFile(cwdEnvPath);
  const homeEnv = loadEnvFile(homeEnvPath);

  const appId = process.env.WECHAT_APP_ID || cwdEnv.WECHAT_APP_ID || homeEnv.WECHAT_APP_ID;
  const appSecret = process.env.WECHAT_APP_SECRET || cwdEnv.WECHAT_APP_SECRET || homeEnv.WECHAT_APP_SECRET;

  if (!appId || !appSecret) {
    throw new Error(
      "Missing WECHAT_APP_ID or WECHAT_APP_SECRET.\n" +
      "Set via environment variables or in .baoyu-skills/.env file."
    );
  }

  return { appId, appSecret };
}

async function fetchAccessToken(appId: string, appSecret: string): Promise<string> {
  const url = `${TOKEN_URL}?grant_type=client_credential&appid=${appId}&secret=${appSecret}`;
  const res = await fetch(url);
  if (!res.ok) {
    throw new Error(`Failed to fetch access token: ${res.status}`);
  }
  const data = await res.json() as AccessTokenResponse;
  if (data.errcode) {
    throw new Error(`Access token error ${data.errcode}: ${data.errmsg}`);
  }
  if (!data.access_token) {
    throw new Error("No access_token in response");
  }
  return data.access_token;
}

async function uploadImage(
  imagePath: string,
  accessToken: string,
  baseDir?: string
): Promise<UploadResponse> {
  let fileBuffer: Buffer;
  let filename: string;
  let contentType: string;

  if (imagePath.startsWith("http://") || imagePath.startsWith("https://")) {
    const response = await fetch(imagePath);
    if (!response.ok) {
      throw new Error(`Failed to download image: ${imagePath}`);
    }
    const buffer = await response.arrayBuffer();
    if (buffer.byteLength === 0) {
      throw new Error(`Remote image is empty: ${imagePath}`);
    }
    fileBuffer = Buffer.from(buffer);
    const urlPath = imagePath.split("?")[0];
    filename = path.basename(urlPath) || "image.jpg";
    contentType = response.headers.get("content-type") || "image/jpeg";
  } else {
    const resolvedPath = path.isAbsolute(imagePath)
      ? imagePath
      : path.resolve(baseDir || process.cwd(), imagePath);

    if (!fs.existsSync(resolvedPath)) {
      throw new Error(`Image not found: ${resolvedPath}`);
    }
    const stats = fs.statSync(resolvedPath);
    if (stats.size === 0) {
      throw new Error(`Local image is empty: ${resolvedPath}`);
    }
    fileBuffer = fs.readFileSync(resolvedPath);
    filename = path.basename(resolvedPath);
    const ext = path.extname(filename).toLowerCase();
    const mimeTypes: Record<string, string> = {
      ".jpg": "image/jpeg",
      ".jpeg": "image/jpeg",
      ".png": "image/png",
      ".gif": "image/gif",
      ".webp": "image/webp",
    };
    contentType = mimeTypes[ext] || "image/jpeg";
  }

  const boundary = `----WebKitFormBoundary${Date.now().toString(16)}`;
  const header = [
    `--${boundary}`,
    `Content-Disposition: form-data; name="media"; filename="${filename}"`,
    `Content-Type: ${contentType}`,
    "",
    "",
  ].join("\r\n");
  const footer = `\r\n--${boundary}--\r\n`;

  const headerBuffer = Buffer.from(header, "utf-8");
  const footerBuffer = Buffer.from(footer, "utf-8");
  const body = Buffer.concat([headerBuffer, fileBuffer, footerBuffer]);

  const url = `${UPLOAD_URL}?access_token=${accessToken}&type=image`;
  const res = await fetch(url, {
    method: "POST",
    headers: {
      "Content-Type": `multipart/form-data; boundary=${boundary}`,
    },
    body,
  });

  const data = await res.json() as UploadResponse;
  if (data.errcode && data.errcode !== 0) {
    throw new Error(`Upload failed ${data.errcode}: ${data.errmsg}`);
  }

  if (data.url?.startsWith("http://")) {
    data.url = data.url.replace(/^http:\/\//i, "https://");
  }

  return data;
}

async function uploadImagesInHtml(
  html: string,
  accessToken: string,
  baseDir: string
): Promise<{ html: string; firstMediaId: string; allMediaIds: string[] }> {
  const imgRegex = /<img[^>]*\ssrc=["']([^"']+)["'][^>]*>/gi;
  const matches = [...html.matchAll(imgRegex)];

  if (matches.length === 0) {
    return { html, firstMediaId: "", allMediaIds: [] };
  }

  let firstMediaId = "";
  let updatedHtml = html;
  const allMediaIds: string[] = [];

  for (const match of matches) {
    const [fullTag, src] = match;
    if (!src) continue;

    if (src.startsWith("https://mmbiz.qpic.cn")) {
      if (!firstMediaId) {
        firstMediaId = src;
      }
      continue;
    }

    const localPathMatch = fullTag.match(/data-local-path=["']([^"']+)["']/);
    const imagePath = localPathMatch ? localPathMatch[1]! : src;

    console.error(`[wechat-api] Uploading image: ${imagePath}`);
    try {
      const resp = await uploadImage(imagePath, accessToken, baseDir);
      const newTag = fullTag
        .replace(/\ssrc=["'][^"']+["']/, ` src="${resp.url}"`)
        .replace(/\sdata-local-path=["'][^"']+["']/, "");
      updatedHtml = updatedHtml.replace(fullTag, newTag);
      allMediaIds.push(resp.media_id);
      if (!firstMediaId) {
        firstMediaId = resp.media_id;
      }
    } catch (err) {
      console.error(`[wechat-api] Failed to upload ${imagePath}:`, err);
    }
  }

  return { html: updatedHtml, firstMediaId, allMediaIds };
}

async function publishToDraft(
  options: ArticleOptions,
  accessToken: string
): Promise<PublishResponse> {
  const url = `${DRAFT_URL}?access_token=${accessToken}`;

  let article: Record<string, unknown>;

  if (options.articleType === "newspic") {
    if (!options.imageMediaIds || options.imageMediaIds.length === 0) {
      throw new Error("newspic requires at least one image");
    }
    article = {
      article_type: "newspic",
      title: options.title,
      content: options.content,
      need_open_comment: options.needOpenComment ? 1 : 0,
      only_fans_can_comment: options.onlyFansCanComment ? 1 : 0,
      image_info: {
        image_list: options.imageMediaIds.map(id => ({ image_media_id: id })),
      },
    };
    if (options.author) article.author = options.author;
  } else {
    article = {
      article_type: "news",
      title: options.title,
      content: options.content,
      thumb_media_id: options.thumbMediaId,
      need_open_comment: options.needOpenComment ? 1 : 0,
      only_fans_can_comment: options.onlyFansCanComment ? 1 : 0,
    };
    if (options.author) article.author = options.author;
    if (options.digest) article.digest = options.digest;
  }

  const res = await fetch(url, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ articles: [article] }),
  });

  const data = await res.json() as PublishResponse;
  if (data.errcode && data.errcode !== 0) {
    throw new Error(`Publish failed ${data.errcode}: ${data.errmsg}`);
  }

  return data;
}

async function batchGetDrafts(
  accessToken: string,
  offset: number,
  count: number,
  noContent = true
): Promise<DraftBatchGetResponse> {
  const url = `${DRAFT_BATCHGET_URL}?access_token=${accessToken}`;
  const res = await fetch(url, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      offset,
      count,
      no_content: noContent ? 1 : 0,
    }),
  });

  const data = await res.json() as DraftBatchGetResponse;
  if (data.errcode && data.errcode !== 0) {
    throw new Error(`Draft batch get failed ${data.errcode}: ${data.errmsg}`);
  }

  return data;
}

async function deleteDraft(accessToken: string, mediaId: string): Promise<void> {
  const url = `${DRAFT_DELETE_URL}?access_token=${accessToken}`;
  const res = await fetch(url, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ media_id: mediaId }),
  });

  const data = await res.json() as DraftDeleteResponse;
  if (data.errcode && data.errcode !== 0) {
    throw new Error(`Draft delete failed ${data.errcode}: ${data.errmsg}`);
  }
}

function extractDraftTitles(item: DraftBatchItem): string[] {
  return (item.content?.news_item || [])
    .map((news) => news.title?.trim() || "")
    .filter(Boolean);
}

async function getAllDrafts(accessToken: string): Promise<DraftBatchItem[]> {
  const all: DraftBatchItem[] = [];
  const batchSize = 20;
  let offset = 0;

  while (true) {
    const resp = await batchGetDrafts(accessToken, offset, batchSize, true);
    const items = resp.item || [];
    all.push(...items);
    if (items.length < batchSize) {
      break;
    }
    offset += items.length;
  }

  return all;
}

function summarizeDraftItem(item: DraftBatchItem): Record<string, unknown> {
  const titles = extractDraftTitles(item);
  const updateTime = item.update_time || 0;
  return {
    media_id: item.media_id,
    titles,
    primary_title: titles[0] || "",
    update_time: updateTime,
    update_time_iso: updateTime ? new Date(updateTime * 1000).toISOString() : null,
  };
}

function parseFrontmatter(content: string): { frontmatter: Record<string, string>; body: string } {
  const match = content.match(/^---\r?\n([\s\S]*?)\r?\n---\r?\n([\s\S]*)$/);
  if (!match) return { frontmatter: {}, body: content };

  const frontmatter: Record<string, string> = {};
  const lines = match[1]!.split("\n");
  for (const line of lines) {
    const colonIdx = line.indexOf(":");
    if (colonIdx > 0) {
      const key = line.slice(0, colonIdx).trim();
      let value = line.slice(colonIdx + 1).trim();
      if ((value.startsWith('"') && value.endsWith('"')) ||
          (value.startsWith("'") && value.endsWith("'"))) {
        value = value.slice(1, -1);
      }
      frontmatter[key] = value;
    }
  }

  return { frontmatter, body: match[2]! };
}

function renderMarkdownToHtml(markdownPath: string, theme: string = "mist-blue", _color?: string, preserveExistingHtml?: boolean): string {
  return renderMarkdownWithPreferredFormatter(markdownPath, {
    theme: normalizePreferredFormatterTheme(theme, "[wechat-api]"),
    outputPath: markdownPath.replace(/\.md$/i, ".wechat-publisher.html"),
    logPrefix: "[wechat-api]",
    preserveExistingHtml,
  });
}

function resolveExistingPath(baseDir: string, value?: string): string | undefined {
  if (!value) return undefined;
  if (value.startsWith("http://") || value.startsWith("https://")) return value;
  const resolved = path.isAbsolute(value) ? value : path.resolve(baseDir, value);
  return fs.existsSync(resolved) ? resolved : undefined;
}

function resolveCoverPath(baseDir: string, explicitCover: string | undefined, frontmatter: Record<string, string>): string | undefined {
  const candidates = [
    resolveExistingPath(process.cwd(), explicitCover),
    resolveExistingPath(baseDir, frontmatter.coverImage),
    resolveExistingPath(baseDir, frontmatter.featureImage),
    resolveExistingPath(baseDir, frontmatter.cover),
    resolveExistingPath(baseDir, frontmatter.image),
    resolveExistingPath(baseDir, "imgs/cover.svg"),
    resolveExistingPath(baseDir, "imgs/cover.png"),
    resolveExistingPath(baseDir, "images/cover-wide.svg"),
    resolveExistingPath(baseDir, "images/cover-wide.png"),
    resolveExistingPath(baseDir, "images/cover.svg"),
    resolveExistingPath(baseDir, "images/cover.png"),
    resolveExistingPath(baseDir, "cover.svg"),
    resolveExistingPath(baseDir, "cover.png"),
  ];
  return prepareWechatCoverPath(candidates.find(Boolean), {
    size: "900x383",
    logPrefix: "[wechat-api]",
  });
}

function extractHtmlContent(htmlPath: string): string {
  const html = fs.readFileSync(htmlPath, "utf-8");
  const match = html.match(/<div id="output">([\s\S]*?)<\/div>\s*<\/body>/);
  if (match) {
    return match[1]!.trim();
  }
  const bodyMatch = html.match(/<body[^>]*>([\s\S]*?)<\/body>/i);
  return bodyMatch ? bodyMatch[1]!.trim() : html;
}

function escapeHtmlText(text: string): string {
  return text
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;");
}

function decodeHtmlEntities(text: string): string {
  return text
    .replace(/&nbsp;/gi, "\u00a0")
    .replace(/&quot;/gi, '"')
    .replace(/&#39;|&apos;/gi, "'")
    .replace(/&lt;/gi, "<")
    .replace(/&gt;/gi, ">")
    .replace(/&amp;/gi, "&");
}

function stripTagsPreserveBreaks(html: string): string {
  return html
    .replace(/<br\s*\/?>/gi, "\n")
    .replace(/<\/p>/gi, "\n")
    .replace(/<\/div>/gi, "\n")
    .replace(/<[^>]+>/g, "");
}

function formatCodeLineForWeChatApi(line: string): string {
  const expanded = line.replace(/\t/g, "    ");
  const leadingMatch = expanded.match(/^ +/);
  const leading = leadingMatch?.[0] || "";
  const remainder = expanded.slice(leading.length);
  const content = `${"&nbsp;".repeat(leading.length)}${escapeHtmlText(remainder)}`;
  return content || "&nbsp;";
}

function buildWeChatApiCodeBlock(rawText: string): string {
  const lines = rawText.replace(/\r\n/g, "\n").replace(/\r/g, "\n").split("\n");
  const safeLines = lines.length > 0 ? lines : [""];
  const lineHtml = safeLines.map((line, idx) => {
    const margin = idx < safeLines.length - 1 ? "0 0 6px 0" : "0";
    return `<p style="margin: ${margin};">${formatCodeLineForWeChatApi(line)}</p>`;
  }).join("");

  return `<section style="background: #282c34; color: #abb2bf; padding: 16px; border-radius: 8px; margin: 16px 0;"><div style="line-height: 1.6; color: #abb2bf; text-align: left; word-break: break-word; overflow-wrap: anywhere; font-family: &quot;SFMono-Regular&quot;, Consolas, &quot;Liberation Mono&quot;, Menlo, Courier, monospace; font-size: 14px; font-weight: 400;">${lineHtml}</div></section>`;
}

function replacePreBlocksForWeChatApi(html: string): string {
  return html.replace(/<pre\b[^>]*>([\s\S]*?)<\/pre>/gi, (_full, inner) => {
    const rawText = decodeHtmlEntities(stripTagsPreserveBreaks(inner))
      .replace(/\u00a0/g, " ")
      .replace(/\n+$/g, "");
    return buildWeChatApiCodeBlock(rawText);
  });
}

function unwrapListItemParagraphs(html: string): string {
  return html
    .replace(/^<p[^>]*>/i, "")
    .replace(/<\/p>$/i, "")
    .trim();
}

function buildWeChatApiList(tag: string, inner: string): string {
  const items = [...inner.matchAll(/<li\b[^>]*>([\s\S]*?)<\/li>/gi)]
    .map((match) => unwrapListItemParagraphs(match[1] || ""))
    .map((item) => item.replace(/^\s+|\s+$/g, ""))
    .filter(Boolean);

  if (items.length === 0) return "";

  return items.map((item, index) => {
    const marker = tag.toLowerCase() === "ol" ? `${index + 1}.` : "•";
    return `<p style="margin: 0 0 14px 0; line-height: 1.9; padding-left: 1.6em; text-indent: -1.6em;">${marker}&nbsp;${item}</p>`;
  }).join("");
}

function normalizeHtmlForWeChatApi(html: string): string {
  let normalized = replacePreBlocksForWeChatApi(html);

  normalized = normalized.replace(/<(ul|ol)([^>]*)>([\s\S]*?)<\/\1>/gi, (_full, tag, attrs, inner) => {
    const compactInner = inner
      .replace(/>\s+</g, "><")
      .replace(/<li([^>]*)>\s*<\/li>/gi, "")
      .replace(/<li([^>]*)>\s+/gi, "<li$1>")
      .replace(/\s+<\/li>/gi, "</li>");
    return buildWeChatApiList(tag, compactInner);
  });

  normalized = normalized.replace(/<p([^>]*)>\s*<\/p>/gi, "");
  normalized = normalized.replace(/\n{3,}/g, "\n\n");
  return normalized.trim();
}

function printUsage(): never {
  console.log(`Publish article to WeChat Official Account draft using API

Usage:
  npx -y bun wechat-api.ts <file> [options]
  npx -y bun wechat-api.ts --draft-list [--offset 0 --count 20]
  npx -y bun wechat-api.ts --draft-delete <media_id>
  npx -y bun wechat-api.ts --draft-delete-title <title> [--keep-latest 1] [--dry-run]

Arguments:
  file                Markdown (.md) or HTML (.html) file

Options:
  --type <type>       Article type: news (文章, default) or newspic (图文)
  --title <title>     Override title
  --author <name>     Author name (max 16 chars)
  --summary <text>    Article summary/digest (max 128 chars)
  --theme <name>      Theme for markdown (mist-blue default, ai-tech optional; legacy names auto-normalize)
  --color <name|hex>  Legacy compatibility option; ignored by the repo-local formatter path
  --cover <path>      Cover image path (local PNG/JPG/WEBP, SVG, or URL)
  --draft-list        List drafts (paged)
  --draft-delete <id> Delete one draft by media_id
  --draft-delete-title <title> Delete drafts whose title exactly matches
  --keep-latest <n>   When deleting by title, keep newest n drafts (default 1)
  --offset <n>        Draft list offset (default 0)
  --count <n>         Draft list page size, max 20 (default 20)
  --dry-run           Parse/render only, or preview draft deletions without deleting
  --help              Show this help

Frontmatter Fields (markdown):
  title               Article title
  author              Author name
  digest/summary      Article summary
  coverImage/featureImage/cover/image   Cover image path (cover.svg auto-renders to PNG)

Comments:
  Comment defaults come from wechat-publisher/EXTEND.md, falling back to open for all users.

Environment Variables:
  WECHAT_APP_ID       WeChat App ID
  WECHAT_APP_SECRET   WeChat App Secret

Config File Locations (in priority order):
  1. Environment variables
  2. <cwd>/.baoyu-skills/.env
  3. ~/.baoyu-skills/.env

Example:
  npx -y bun wechat-api.ts article.md
  npx -y bun wechat-api.ts article.md --theme mist-blue --cover cover.png
  npx -y bun wechat-api.ts article.md --cover imgs/cover.svg
  npx -y bun wechat-api.ts article.md --author "Author Name" --summary "Brief intro"
  npx -y bun wechat-api.ts article.html --title "My Article"
  npx -y bun wechat-api.ts images/ --type newspic --title "Photo Album"
  npx -y bun wechat-api.ts article.md --dry-run
  npx -y bun wechat-api.ts --draft-list --count 10
  npx -y bun wechat-api.ts --draft-delete MEDIA_ID
  npx -y bun wechat-api.ts --draft-delete-title "OpenClaw 通道实战：先接一个真正能用的消息入口" --keep-latest 1 --dry-run
`);
  process.exit(0);
}

interface CliArgs {
  command: CommandMode;
  filePath: string;
  isHtml: boolean;
  articleType: ArticleType;
  title?: string;
  author?: string;
  summary?: string;
  theme?: string;
  color?: string;
  cover?: string;
  dryRun: boolean;
  draftMediaId?: string;
  draftTitle?: string;
  keepLatest: number;
  offset: number;
  count: number;
}

function parseArgs(argv: string[]): CliArgs {
  if (argv.length === 0 || argv.includes("--help") || argv.includes("-h")) {
    printUsage();
  }

  const args: CliArgs = {
    command: "publish",
    filePath: "",
    isHtml: false,
    articleType: "news",
    dryRun: false,
    keepLatest: 1,
    offset: 0,
    count: 20,
  };

  for (let i = 0; i < argv.length; i++) {
    const arg = argv[i]!;
    if (arg === "--draft-list") {
      args.command = "draft-list";
    } else if (arg === "--draft-delete" && argv[i + 1]) {
      args.command = "draft-delete";
      args.draftMediaId = argv[++i];
    } else if (arg === "--draft-delete-title" && argv[i + 1]) {
      args.command = "draft-delete-title";
      args.draftTitle = argv[++i];
    } else if (arg === "--keep-latest" && argv[i + 1]) {
      const parsed = parseInt(argv[++i]!, 10);
      if (!Number.isNaN(parsed) && parsed >= 0) args.keepLatest = parsed;
    } else if (arg === "--offset" && argv[i + 1]) {
      const parsed = parseInt(argv[++i]!, 10);
      if (!Number.isNaN(parsed) && parsed >= 0) args.offset = parsed;
    } else if (arg === "--count" && argv[i + 1]) {
      const parsed = parseInt(argv[++i]!, 10);
      if (!Number.isNaN(parsed) && parsed > 0) args.count = Math.min(parsed, 20);
    } else if (arg === "--type" && argv[i + 1]) {
      const t = argv[++i]!.toLowerCase();
      if (t === "news" || t === "newspic") {
        args.articleType = t;
      }
    } else if (arg === "--title" && argv[i + 1]) {
      args.title = argv[++i];
    } else if (arg === "--author" && argv[i + 1]) {
      args.author = argv[++i];
    } else if (arg === "--summary" && argv[i + 1]) {
      args.summary = argv[++i];
    } else if (arg === "--theme" && argv[i + 1]) {
      args.theme = argv[++i]!;
    } else if (arg === "--color" && argv[i + 1]) {
      args.color = argv[++i];
    } else if (arg === "--cover" && argv[i + 1]) {
      args.cover = argv[++i];
    } else if (arg === "--dry-run") {
      args.dryRun = true;
    } else if (arg.startsWith("--") && argv[i + 1] && !argv[i + 1]!.startsWith("-")) {
      i++;
    } else if (!arg.startsWith("-")) {
      args.filePath = arg;
    }
  }

  if (args.command === "publish") {
    if (!args.filePath) {
      console.error("Error: File path required");
      process.exit(1);
    }
    args.isHtml = args.filePath.toLowerCase().endsWith(".html");
  } else {
    if (args.command === "draft-delete" && !args.draftMediaId) {
      console.error("Error: --draft-delete requires a media_id");
      process.exit(1);
    }
    if (args.command === "draft-delete-title" && !args.draftTitle) {
      console.error("Error: --draft-delete-title requires a title");
      process.exit(1);
    }
  }

  return args;
}

function extractHtmlTitle(html: string): string {
  const titleMatch = html.match(/<title>([^<]+)<\/title>/i);
  if (titleMatch) return titleMatch[1]!;
  const h1Match = html.match(/<h1[^>]*>([^<]+)<\/h1>/i);
  if (h1Match) return h1Match[1]!.replace(/<[^>]+>/g, "").trim();
  return "";
}

async function main(): Promise<void> {
  const args = parseArgs(process.argv.slice(2));
  const extendConfig = loadExtendConfig();
  const resolvedTheme = normalizePreferredFormatterTheme(args.theme || extendConfig.defaultTheme, "[wechat-api]");
  const resolvedColor = args.color || extendConfig.defaultColor;
  const needOpenComment = extendConfig.needOpenComment ?? true;
  const onlyFansCanComment = extendConfig.onlyFansCanComment ?? false;

  if (args.command !== "publish") {
    const config = loadConfig();
    console.error("[wechat-api] Fetching access token...");
    const accessToken = await fetchAccessToken(config.appId, config.appSecret);

    if (args.command === "draft-list") {
      const result = await batchGetDrafts(accessToken, args.offset, args.count, true);
      const items = (result.item || []).map(summarizeDraftItem);
      console.log(JSON.stringify({
        success: true,
        operation: "draft-list",
        offset: args.offset,
        count: args.count,
        total_count: result.total_count || 0,
        item_count: result.item_count || items.length,
        items,
      }, null, 2));
      return;
    }

    if (args.command === "draft-delete") {
      if (args.dryRun) {
        console.log(JSON.stringify({
          success: true,
          operation: "draft-delete-dry-run",
          media_id: args.draftMediaId,
        }, null, 2));
        return;
      }

      console.error(`[wechat-api] Deleting draft: ${args.draftMediaId}`);
      await deleteDraft(accessToken, args.draftMediaId!);
      console.log(JSON.stringify({
        success: true,
        operation: "draft-delete",
        media_id: args.draftMediaId,
      }, null, 2));
      return;
    }

    const allDrafts = await getAllDrafts(accessToken);
    const matched = allDrafts
      .filter((item) => extractDraftTitles(item).some((title) => title === args.draftTitle))
      .sort((a, b) => (b.update_time || 0) - (a.update_time || 0));

    const keep = matched.slice(0, args.keepLatest).map(summarizeDraftItem);
    const toDelete = matched.slice(args.keepLatest).map(summarizeDraftItem);

    if (args.dryRun) {
      console.log(JSON.stringify({
        success: true,
        operation: "draft-delete-title-dry-run",
        title: args.draftTitle,
        keep_latest: args.keepLatest,
        matched_count: matched.length,
        keep,
        delete: toDelete,
      }, null, 2));
      return;
    }

    for (const item of matched.slice(args.keepLatest)) {
      console.error(`[wechat-api] Deleting old draft: ${item.media_id}`);
      await deleteDraft(accessToken, item.media_id);
    }

    console.log(JSON.stringify({
      success: true,
      operation: "draft-delete-title",
      title: args.draftTitle,
      keep_latest: args.keepLatest,
      matched_count: matched.length,
      deleted_count: Math.max(matched.length - args.keepLatest, 0),
      keep,
      delete: toDelete,
    }, null, 2));
    return;
  }

  const filePath = path.resolve(args.filePath);
  if (!fs.existsSync(filePath)) {
    console.error(`Error: File not found: ${filePath}`);
    process.exit(1);
  }

  const baseDir = path.dirname(filePath);
  let title = args.title || "";
  let author = args.author || "";
  let digest = args.summary || "";
  let htmlPath: string;
  let htmlContent: string;
  let frontmatter: Record<string, string> = {};

  if (args.isHtml) {
    htmlPath = filePath;
    htmlContent = normalizeHtmlForWeChatApi(extractHtmlContent(htmlPath));
    let mdPath = filePath.replace(/\.html$/i, ".md");
    if (!fs.existsSync(mdPath)) {
      mdPath = filePath.replace(/\.wechat-publisher\.html$/i, ".md");
    }
    if (fs.existsSync(mdPath)) {
      const mdContent = fs.readFileSync(mdPath, "utf-8");
      const parsed = parseFrontmatter(mdContent);
      frontmatter = parsed.frontmatter;
      if (!title && frontmatter.title) title = frontmatter.title;
      if (!author) author = frontmatter.author || "";
      if (!digest) digest = frontmatter.digest || frontmatter.summary || frontmatter.description || "";
    }
    if (!title) {
      title = extractHtmlTitle(fs.readFileSync(htmlPath, "utf-8"));
    }
    console.error(`[wechat-api] Using HTML file: ${htmlPath}`);
  } else {
    const content = fs.readFileSync(filePath, "utf-8");
    const parsed = parseFrontmatter(content);
    frontmatter = parsed.frontmatter;
    const body = parsed.body;

    title = title || frontmatter.title || "";
    if (!title) {
      const h1Match = body.match(/^#\s+(.+)$/m);
      if (h1Match) title = h1Match[1]!;
    }
    if (!author) author = frontmatter.author || "";
    if (!digest) digest = frontmatter.digest || frontmatter.summary || frontmatter.description || "";

    console.error(`[wechat-api] Theme: ${resolvedTheme}${resolvedColor ? `, color: ${resolvedColor}` : ""}`);
    htmlPath = renderMarkdownToHtml(filePath, resolvedTheme, resolvedColor, !args.theme);
    console.error(`[wechat-api] HTML generated: ${htmlPath}`);
    htmlContent = normalizeHtmlForWeChatApi(extractHtmlContent(htmlPath));
  }

  if (!author) author = extendConfig.defaultAuthor || "";

  if (!title) {
    console.error("Error: No title found. Provide via --title, frontmatter, or <title> tag.");
    process.exit(1);
  }

  if (digest && digest.length > 120) {
    const truncated = digest.slice(0, 117);
    const lastPunct = Math.max(truncated.lastIndexOf("。"), truncated.lastIndexOf("，"), truncated.lastIndexOf("；"), truncated.lastIndexOf("、"));
    digest = lastPunct > 80 ? truncated.slice(0, lastPunct + 1) : truncated + "...";
    console.error(`[wechat-api] Digest truncated to ${digest.length} chars`);
  }

  console.error(`[wechat-api] Title: ${title}`);
  if (author) console.error(`[wechat-api] Author: ${author}`);
  if (digest) console.error(`[wechat-api] Digest: ${digest.slice(0, 50)}...`);
  console.error(`[wechat-api] Type: ${args.articleType}`);
  console.error(
    `[wechat-api] Comments: ${needOpenComment ? "open" : "closed"}, ${onlyFansCanComment ? "fans-only" : "all-users"}`
  );

  if (args.dryRun) {
    console.log(JSON.stringify({
      articleType: args.articleType,
      title,
      author: author || undefined,
      digest: digest || undefined,
      htmlPath,
      contentLength: htmlContent.length,
      theme: resolvedTheme,
      color: resolvedColor,
      needOpenComment,
      onlyFansCanComment,
    }, null, 2));
    return;
  }

  const config = loadConfig();
  console.error("[wechat-api] Fetching access token...");
  const accessToken = await fetchAccessToken(config.appId, config.appSecret);

  console.error("[wechat-api] Uploading images...");
  const { html: processedHtml, firstMediaId, allMediaIds } = await uploadImagesInHtml(
    htmlContent,
    accessToken,
    baseDir
  );
  htmlContent = processedHtml;

  let thumbMediaId = "";
  const coverPath = resolveCoverPath(baseDir, args.cover, frontmatter);

  if (coverPath) {
    console.error(`[wechat-api] Uploading cover: ${coverPath}`);
    const coverResp = await uploadImage(coverPath, accessToken, baseDir);
    thumbMediaId = coverResp.media_id;
  } else if (firstMediaId) {
    if (firstMediaId.startsWith("https://")) {
      console.error(`[wechat-api] Uploading first image as cover: ${firstMediaId}`);
      const coverResp = await uploadImage(firstMediaId, accessToken, baseDir);
      thumbMediaId = coverResp.media_id;
    } else {
      thumbMediaId = firstMediaId;
    }
  }

  if (args.articleType === "news" && !thumbMediaId) {
    console.error("Error: No cover image. Provide via --cover, frontmatter.coverImage, or include an image in content.");
    process.exit(1);
  }

  if (args.articleType === "newspic" && allMediaIds.length === 0) {
    console.error("Error: newspic requires at least one image in content.");
    process.exit(1);
  }

  console.error("[wechat-api] Publishing to draft...");
  const result = await publishToDraft({
    title,
    author: author || undefined,
    digest: digest || undefined,
    content: htmlContent,
    thumbMediaId,
    articleType: args.articleType,
    imageMediaIds: args.articleType === "newspic" ? allMediaIds : undefined,
    needOpenComment,
    onlyFansCanComment,
  }, accessToken);

  console.log(JSON.stringify({
    success: true,
    media_id: result.media_id,
    title,
    articleType: args.articleType,
  }, null, 2));

  console.error(`[wechat-api] Published successfully! media_id: ${result.media_id}`);
}

await main().catch((err) => {
  console.error(`Error: ${err instanceof Error ? err.message : String(err)}`);
  process.exit(1);
});
