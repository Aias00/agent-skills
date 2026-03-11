#!/usr/bin/env bun

import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import { spawnSync } from "node:child_process";

type PublishMethod = "api" | "browser";
type SourceKind = "markdown" | "html";

interface ExtendConfig {
  defaultPublishMethod?: PublishMethod;
  defaultTheme?: string;
  defaultColor?: string;
  defaultAuthor?: string;
  chromeProfilePath?: string;
}

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
  dryRun: boolean;
}

interface ResolvedSource {
  path: string;
  kind: SourceKind;
}

const SKILL_DIR = path.dirname(import.meta.path);
const WECHAT_API = path.join(SKILL_DIR, "wechat-api.ts");
const WECHAT_ARTICLE = path.join(SKILL_DIR, "wechat-article.ts");

function loadExtendConfig(): ExtendConfig {
  const extendPaths = [
    path.join(process.cwd(), ".baoyu-skills", "wechat-publisher", "EXTEND.md"),
    path.join(os.homedir(), ".baoyu-skills", "wechat-publisher", "EXTEND.md"),
  ];
  const extendPath = extendPaths.find((candidate) => fs.existsSync(candidate));
  if (!extendPath) return {};

  const config: ExtendConfig = {};
  const content = fs.readFileSync(extendPath, "utf-8");
  for (const rawLine of content.split("\n")) {
    const line = rawLine.trim();
    if (!line || line.startsWith("#")) continue;
    const colonIdx = line.indexOf(":");
    if (colonIdx <= 0) continue;

    const key = line.slice(0, colonIdx).trim().toLowerCase();
    const value = line.slice(colonIdx + 1).trim();
    if (!value) continue;

    if (key === "default_publish_method" && (value === "api" || value === "browser")) {
      config.defaultPublishMethod = value;
    } else if (key === "default_theme") {
      config.defaultTheme = value;
    } else if (key === "default_color") {
      config.defaultColor = value;
    } else if (key === "default_author") {
      config.defaultAuthor = value;
    } else if (key === "chrome_profile_path") {
      config.chromeProfilePath = value;
    }
  }

  return config;
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
  if (ext === ".md") return { path: resolved, kind: "markdown" };
  if (ext === ".html" || ext === ".htm") return { path: resolved, kind: "html" };
  throw new Error(`Unsupported source type for WeChat publishing: ${resolved}`);
}

function buildApiCommand(source: ResolvedSource, options: CliOptions, extend: ExtendConfig): string[] {
  const cmd = ["bun", WECHAT_API, source.path];
  const title = options.title;
  const summary = options.summary;
  const author = options.author || extend.defaultAuthor;
  const theme = options.theme || extend.defaultTheme;
  const color = options.color || extend.defaultColor;

  if (title) cmd.push("--title", title);
  if (summary) cmd.push("--summary", summary);
  if (author) cmd.push("--author", author);
  if (options.cover) cmd.push("--cover", path.resolve(options.cover));
  if (theme) cmd.push("--theme", theme);
  if (color) cmd.push("--color", color);
  if (options.dryRun) cmd.push("--dry-run");
  return cmd;
}

function buildBrowserCommand(source: ResolvedSource, options: CliOptions, extend: ExtendConfig): string[] {
  const cmd = ["bun", WECHAT_ARTICLE];
  if (source.kind === "markdown") cmd.push("--markdown", source.path);
  else cmd.push("--html", source.path);

  const author = options.author || extend.defaultAuthor;
  const theme = options.theme || extend.defaultTheme;
  const color = options.color || extend.defaultColor;
  const profile = options.profile || extend.chromeProfilePath;

  if (options.title) cmd.push("--title", options.title);
  if (options.summary) cmd.push("--summary", options.summary);
  if (author) cmd.push("--author", author);
  if (options.cover) cmd.push("--cover", path.resolve(options.cover));
  if (theme) cmd.push("--theme", theme);
  if (color) cmd.push("--color", color);
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
  --title <text>               Override article title
  --summary <text>             Override article summary
  --author <name>              Override author
  --cover <path>               Override cover image path
  --theme <name>               Override theme
  --color <name|hex>           Override color
  --profile <dir>              Override Chrome profile for browser mode
  --dry-run                    Print resolved command without publishing
  -h, --help                   Show help

Examples:
  npx -y bun wechat-publish.ts ./article-package
  npx -y bun wechat-publish.ts article.md --method browser
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
  const cmd = method === "api"
    ? buildApiCommand(source, options, extend)
    : buildBrowserCommand(source, options, extend);

  if (options.dryRun) {
    console.log(JSON.stringify({
      ok: true,
      method,
      source: source.path,
      command: cmd,
    }, null, 2));
    return;
  }

  let result = runCommand(cmd);
  echoResult(result);

  const canFallback = options.method !== "api" && method === "api" && isWechatApiWhitelistError(result);
  if (canFallback) {
    console.error("[wechat-publish] API blocked by IP whitelist. Falling back to browser publishing...");
    const browserSource = resolveSource(options.source, "browser");
    const browserCmd = buildBrowserCommand(browserSource, options, extend);
    result = runCommand(browserCmd);
    echoResult(result);
  }

  process.exit(result.status ?? 1);
}

main();
