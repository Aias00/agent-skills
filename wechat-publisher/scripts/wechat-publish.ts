#!/usr/bin/env bun

import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import { spawnSync } from "node:child_process";
import { renderMarkdownWithPreferredFormatter } from "./preferred-markdown-render.ts";
import {
  loadWechatPublisherExtendConfig,
  type WechatPublisherExtendConfig,
} from "./wechat-extend-config.ts";

type PublishMethod = "api" | "browser";
type SourceKind = "markdown" | "html";
type ExtendConfig = WechatPublisherExtendConfig;

interface CliOptions {
  source: string;
  method?: PublishMethod | "auto";
  title?: string;
  summary?: string;
  author?: string;
  cover?: string;
  theme?: string;
  color?: string;
  profile?: string;
  legacyMarkdownRenderer?: boolean;
  dryRun: boolean;
}

interface ResolvedSource {
  path: string;
  kind: SourceKind;
  /** Original markdown path before formatter conversion, used for title/frontmatter derivation. */
  markdownPath?: string;
}

const SKILL_DIR = path.dirname(import.meta.path);
const WECHAT_API = path.join(SKILL_DIR, "wechat-api.ts");
const WECHAT_ARTICLE = path.join(SKILL_DIR, "wechat-article.ts");

function loadExtendConfig(): ExtendConfig {
  return loadWechatPublisherExtendConfig();
}

function loadEnvFile(envPath: string): Record<string, string> {
  const env: Record<string, string> = {};
  if (!fs.existsSync(envPath)) return env;

  const content = fs.readFileSync(envPath, "utf-8");
  for (const raw of content.split("\n")) {
    const line = raw.trim();
    if (!line || line.startsWith("#")) continue;
    const idx = line.indexOf("=");
    if (idx <= 0) continue;
    const key = line.slice(0, idx).trim();
    const value = line.slice(idx + 1).trim().replace(/^['"]|['"]$/g, "");
    env[key] = value;
  }
  return env;
}

function hasWechatApiCredentials(): boolean {
  const cwdEnv = loadEnvFile(path.join(process.cwd(), ".baoyu-skills", ".env"));
  const homeEnv = loadEnvFile(path.join(os.homedir(), ".baoyu-skills", ".env"));
  return Boolean(
    process.env.WECHAT_APP_ID ||
    cwdEnv.WECHAT_APP_ID ||
    homeEnv.WECHAT_APP_ID
  ) && Boolean(
    process.env.WECHAT_APP_SECRET ||
    cwdEnv.WECHAT_APP_SECRET ||
    homeEnv.WECHAT_APP_SECRET
  );
}

function chooseExisting(baseDir: string, names: string[]): string | undefined {
  for (const name of names) {
    const candidate = path.join(baseDir, name);
    if (fs.existsSync(candidate)) return candidate;
  }
  return undefined;
}

function formatMarkdownWithPreferredFormatter(
  source: ResolvedSource,
  options: CliOptions,
  extend: ExtendConfig,
): ResolvedSource {
  if (source.kind !== "markdown") return source;
  if (options.legacyMarkdownRenderer) return source;

  const theme = options.theme || extend.defaultTheme || "mist-blue";
  const outputPath = renderMarkdownWithPreferredFormatter(source.path, {
    theme,
    outputPath: source.path.replace(/\.md$/i, ".wechat-publisher.html"),
    logPrefix: "[wechat-publish]",
    preserveExistingHtml: !options.theme,
  });
  return { path: outputPath, kind: "html", markdownPath: source.path };
}

function resolveSource(inputPath: string, method: PublishMethod): ResolvedSource {
  const resolved = path.resolve(inputPath);
  if (!fs.existsSync(resolved)) {
    throw new Error(`Source not found: ${resolved}`);
  }

  if (fs.statSync(resolved).isDirectory()) {
    const candidates = method === "browser"
      ? ["article-preview.md", "article.md", "article-wechat.html", "article.html", "article-api.html"]
      : ["article-api.html", "article-wechat.html", "article.html", "article.md", "article-preview.md"];
    const match = chooseExisting(resolved, candidates);
    if (!match) {
      throw new Error(`No WeChat article source found under ${resolved}`);
    }
    return resolveSource(match, method);
  }

  const ext = path.extname(resolved).toLowerCase();
  if (ext === ".md") return { path: resolved, kind: "markdown", markdownPath: resolved };
  if (ext === ".html" || ext === ".htm") {
    // For an HTML source, remember a sibling .md if present so we can still derive
    // a title from frontmatter/H1 instead of falling back to the (often generic) <title>.
    const siblingMd = resolved.replace(/\.wechat-publisher\.html$/i, ".md").replace(/\.html?$/i, ".md");
    const markdownPath = fs.existsSync(siblingMd) ? siblingMd : undefined;
    return { path: resolved, kind: "html", markdownPath };
  }
  throw new Error(`Unsupported source type for WeChat publishing: ${resolved}`);
}

/**
 * Derive an article title from a markdown file: frontmatter `title` first, then
 * the first H1. Returns undefined when nothing usable is found, so the caller
 * can fall back to wechat-api's own <title> extraction. Mirrors the logic in
 * wechat-api.ts so the two stay consistent.
 */
function deriveTitleFromMarkdown(markdownPath: string): string | undefined {
  if (!markdownPath || !fs.existsSync(markdownPath)) return undefined;
  const content = fs.readFileSync(markdownPath, "utf-8");
  const fmMatch = content.match(/^---\r?\n([\s\S]*?)\r?\n---\r?\n/);
  if (fmMatch) {
    for (const line of fmMatch[1]!.split("\n")) {
      const colonIdx = line.indexOf(":");
      if (colonIdx <= 0) continue;
      const key = line.slice(0, colonIdx).trim();
      if (key === "title") {
        let value = line.slice(colonIdx + 1).trim();
        if ((value.startsWith('"') && value.endsWith('"')) ||
            (value.startsWith("'") && value.endsWith("'"))) {
          value = value.slice(1, -1);
        }
        if (value) return value;
      }
    }
  }
  const h1Match = content.match(/^#\s+(.+)$/m);
  return h1Match ? h1Match[1]!.trim() : undefined;
}

function buildApiCommand(source: ResolvedSource, options: CliOptions, extend: ExtendConfig): string[] {
  const cmd = ["bun", WECHAT_API, source.path];
  const title = options.title || deriveTitleFromMarkdown(source.markdownPath || "");
  const summary = options.summary;
  const author = options.author || extend.defaultAuthor;
  const theme = options.theme || extend.defaultTheme;
  const color = options.color || extend.defaultColor;
  const needsMarkdownRenderFlags = source.kind === "markdown";

  if (title) cmd.push("--title", title);
  if (summary) cmd.push("--summary", summary);
  if (author) cmd.push("--author", author);
  if (options.cover) cmd.push("--cover", path.resolve(options.cover));
  if (needsMarkdownRenderFlags && theme) cmd.push("--theme", theme);
  if (needsMarkdownRenderFlags && color) cmd.push("--color", color);
  if (options.dryRun) cmd.push("--dry-run");
  return cmd;
}

function buildBrowserCommand(source: ResolvedSource, options: CliOptions, extend: ExtendConfig): string[] {
  const cmd = ["bun", WECHAT_ARTICLE];
  if (source.kind === "markdown") cmd.push("--markdown", source.path);
  else cmd.push("--html", source.path);

  const title = options.title || deriveTitleFromMarkdown(source.markdownPath || "");
  const author = options.author || extend.defaultAuthor;
  const theme = options.theme || extend.defaultTheme;
  const color = options.color || extend.defaultColor;
  const profile = options.profile || extend.chromeProfilePath;
  const needsMarkdownRenderFlags = source.kind === "markdown";

  if (title) cmd.push("--title", title);
  if (options.summary) cmd.push("--summary", options.summary);
  if (author) cmd.push("--author", author);
  if (options.cover) cmd.push("--cover", path.resolve(options.cover));
  if (needsMarkdownRenderFlags && theme) cmd.push("--theme", theme);
  if (needsMarkdownRenderFlags && color) cmd.push("--color", color);
  if (profile) cmd.push("--profile", profile);
  cmd.push("--submit");
  return cmd;
}

function runCommand(cmd: string[]): ReturnType<typeof spawnSync> {
  return spawnSync(cmd[0], cmd.slice(1), {
    stdio: "pipe",
    encoding: "utf-8",
  });
}

function echoResult(result: ReturnType<typeof spawnSync>) {
  if (result.stdout) process.stdout.write(result.stdout);
  if (result.stderr) process.stderr.write(result.stderr);
}

function isWechatApiWhitelistError(result: ReturnType<typeof spawnSync>): boolean {
  const text = `${result.stdout || ""}\n${result.stderr || ""}`.toLowerCase();
  return text.includes("invalid ip") || text.includes("not in whitelist");
}

function resolveMethod(options: CliOptions, extend: ExtendConfig): PublishMethod {
  if (options.method === "api" || options.method === "browser") {
    return options.method;
  }
  if (extend.defaultPublishMethod) return extend.defaultPublishMethod;
  return hasWechatApiCredentials() ? "api" : "browser";
}

function printUsage(): never {
  console.log(`
Usage:
  npx -y bun wechat-publish.ts <source> [options]

Options:
  --method <api|browser|auto>  Publish method. Default: EXTEND.md or auto
  --title <text>               Override article title (defaults to frontmatter title or first H1)
  --summary <text>             Override article summary
  --author <name>              Override author
  --cover <path>               Override cover image path
  --theme <name>               Override markdown theme (mist-blue default, ai-tech optional)
  --color <name|hex>           Legacy compatibility option; ignored by the preferred formatter path
  --profile <dir>              Override Chrome profile for browser mode
  --legacy-markdown-renderer   Skip repo-local formatter and use legacy markdown publish path
  --dry-run                    Print resolved command without publishing
  -h, --help                   Show help

Examples:
  npx -y bun wechat-publish.ts ./article-package
  npx -y bun wechat-publish.ts article.md --method browser
  npx -y bun wechat-publish.ts article.md --legacy-markdown-renderer
  npx -y bun wechat-publish.ts article-api.html --title "My Title" --cover imgs/cover.png
`);
  process.exit(0);
}

function parseArgs(argv: string[]): CliOptions {
  if (argv.includes("-h") || argv.includes("--help")) printUsage();
  if (argv.length === 0) {
    console.error("Error: source is required.");
    printUsage();
  }

  const options: CliOptions = {
    source: "",
    dryRun: false,
  };

  const args = [...argv];
  if (args[0] && !args[0].startsWith("-")) {
    options.source = args.shift()!;
  }

  if (!options.source) {
    console.error("Error: source is required.");
    process.exit(1);
  }

  for (let i = 0; i < args.length; i++) {
    const arg = args[i];
    if (arg === "--method" && args[i + 1]) options.method = args[++i] as CliOptions["method"];
    else if (arg === "--title" && args[i + 1]) options.title = args[++i];
    else if (arg === "--summary" && args[i + 1]) options.summary = args[++i];
    else if (arg === "--author" && args[i + 1]) options.author = args[++i];
    else if (arg === "--cover" && args[i + 1]) options.cover = args[++i];
    else if (arg === "--theme" && args[i + 1]) options.theme = args[++i];
    else if (arg === "--color" && args[i + 1]) options.color = args[++i];
    else if (arg === "--profile" && args[i + 1]) options.profile = args[++i];
    else if (arg === "--legacy-markdown-renderer") options.legacyMarkdownRenderer = true;
    else if (arg === "--dry-run") options.dryRun = true;
    else {
      console.error(`Unknown argument: ${arg}`);
      process.exit(1);
    }
  }

  return options;
}

function main() {
  const options = parseArgs(process.argv.slice(2));
  const extend = loadExtendConfig();
  const method = resolveMethod(options, extend);
  const source = resolveSource(options.source, method);
  const publishSource = formatMarkdownWithPreferredFormatter(source, options, extend);
  const cmd = method === "api"
    ? buildApiCommand(publishSource, options, extend)
    : buildBrowserCommand(publishSource, options, extend);

  if (options.dryRun) {
    console.log(JSON.stringify({
      ok: true,
      method,
      source: publishSource.path,
      command: cmd,
    }, null, 2));
    return;
  }

  let result = runCommand(cmd);
  echoResult(result);

  const canFallback = options.method !== "api" && method === "api" && isWechatApiWhitelistError(result);
  if (canFallback) {
    console.error("[wechat-publish] API blocked by IP whitelist. Falling back to browser publishing...");
    const browserSource = formatMarkdownWithPreferredFormatter(resolveSource(options.source, "browser"), options, extend);
    const browserCmd = buildBrowserCommand(browserSource, options, extend);
    result = runCommand(browserCmd);
    echoResult(result);
  }

  process.exit(result.status ?? 1);
}

main();
