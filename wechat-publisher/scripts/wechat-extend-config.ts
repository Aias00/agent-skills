import fs from "node:fs";
import os from "node:os";
import path from "node:path";

const SCRIPT_DIR = path.dirname(import.meta.path);
const REPO_ROOT = path.resolve(SCRIPT_DIR, "..", "..");

export function findWechatPublisherExtendPath(): string | undefined {
  const candidates: string[] = [
    path.join(process.cwd(), ".baoyu-skills", "wechat-publisher", "EXTEND.md"),
    path.join(os.homedir(), ".baoyu-skills", "wechat-publisher", "EXTEND.md"),
    path.join(REPO_ROOT, ".baoyu-skills", "wechat-publisher", "EXTEND.md"),
  ];

  let dir = process.cwd();
  for (let depth = 0; depth < 8; depth += 1) {
    candidates.push(path.join(dir, ".baoyu-skills", "wechat-publisher", "EXTEND.md"));
    const parent = path.dirname(dir);
    if (parent === dir) break;
    dir = parent;
  }

  return candidates.find((candidate) => fs.existsSync(candidate));
}

export function parseBool(value?: string): boolean | undefined {
  if (!value) return undefined;
  const normalized = value.trim().toLowerCase();
  if (["1", "true", "yes", "on"].includes(normalized)) return true;
  if (["0", "false", "no", "off"].includes(normalized)) return false;
  return undefined;
}

export interface WechatPublisherExtendConfig {
  defaultPublishMethod?: "api" | "browser";
  defaultTheme?: string;
  defaultColor?: string;
  defaultAuthor?: string;
  chromeProfilePath?: string;
  needOpenComment?: boolean;
  onlyFansCanComment?: boolean;
}

export function loadWechatPublisherExtendConfig(): WechatPublisherExtendConfig {
  const extendPath = findWechatPublisherExtendPath();
  if (!extendPath) return {};

  const config: WechatPublisherExtendConfig = {};
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
    } else if (key === "need_open_comment") {
      config.needOpenComment = parseBool(value);
    } else if (key === "only_fans_can_comment") {
      config.onlyFansCanComment = parseBool(value);
    }
  }

  return config;
}