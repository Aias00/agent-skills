import fs from "node:fs";
import path from "node:path";
import { spawnSync } from "node:child_process";

const SCRIPT_DIR = path.dirname(import.meta.path);
const REPO_ROOT = path.resolve(SCRIPT_DIR, "..", "..");
const FORMATTER_DIR = path.join(REPO_ROOT, "wechat-article-formatter");
const FORMATTER_SCRIPT = path.join(FORMATTER_DIR, "scripts", "markdown_to_html.py");
const FORMATTER_VENV_PYTHON = process.platform === "win32"
  ? path.join(FORMATTER_DIR, ".venv", "Scripts", "python.exe")
  : path.join(FORMATTER_DIR, ".venv", "bin", "python");
const PREFERRED_THEMES = new Set(["mist-blue", "ai-tech"]);
const LEGACY_THEME_ALIASES = new Set(["default", "grace", "simple", "modern"]);

function pythonHasFormatterDeps(pythonBin: string): boolean {
  const result = spawnSync(
    pythonBin,
    ["-c", "import markdown, bs4, cssutils, lxml"],
    { stdio: "pipe", encoding: "utf-8" },
  );
  return result.status === 0;
}

export function normalizePreferredFormatterTheme(theme?: string, logPrefix = "[wechat]"): string {
  const normalized = theme?.trim().toLowerCase();
  if (!normalized) return "mist-blue";
  if (PREFERRED_THEMES.has(normalized)) return normalized;
  if (LEGACY_THEME_ALIASES.has(normalized)) {
    console.error(`${logPrefix} Legacy markdown theme "${normalized}" detected. Using "mist-blue" with the repo-local formatter.`);
    return "mist-blue";
  }
  console.error(`${logPrefix} Unknown markdown theme "${theme}". Using "mist-blue" with the repo-local formatter.`);
  return "mist-blue";
}

export function resolvePreferredFormatterPython(): string | undefined {
  const candidates = [
    FORMATTER_VENV_PYTHON,
    "python3",
    "python",
  ];
  for (const candidate of candidates) {
    if (pythonHasFormatterDeps(candidate)) return candidate;
  }
  return undefined;
}

export function renderMarkdownWithPreferredFormatter(
  markdownPath: string,
  options: { theme?: string; outputPath?: string; logPrefix?: string } = {},
): string {
  if (!fs.existsSync(FORMATTER_SCRIPT)) {
    throw new Error(
      `Preferred formatter not found: ${FORMATTER_SCRIPT}\n` +
      `Expected repo-local wechat-article-formatter.`
    );
  }

  const pythonBin = resolvePreferredFormatterPython();
  if (!pythonBin) {
    throw new Error(
      "No usable Python runtime found for wechat-article-formatter.\n" +
      `Expected ${FORMATTER_VENV_PYTHON} or a working python3/python in PATH with formatter dependencies installed.\n` +
      `Run bootstrap first: cd ${path.join(REPO_ROOT, "wechat-publisher")} && bun scripts/bootstrap-local.ts --project-root ${REPO_ROOT}`
    );
  }

  const theme = normalizePreferredFormatterTheme(options.theme, options.logPrefix || "[wechat]");
  const outputPath = options.outputPath || markdownPath.replace(/\.md$/i, ".wechat-publisher.html");
  const logPrefix = options.logPrefix || "[wechat]";
  const args = [
    FORMATTER_SCRIPT,
    "--input", markdownPath,
    "--output", outputPath,
    "--theme", theme,
  ];

  const result = spawnSync(pythonBin, args, {
    stdio: ["inherit", "pipe", "pipe"],
    encoding: "utf-8",
    cwd: REPO_ROOT,
  });

  if (result.status !== 0 || !fs.existsSync(outputPath)) {
    const stderr = result.stderr?.trim();
    const stdout = result.stdout?.trim();
    throw new Error(
      `${logPrefix} preferred formatter failed.\n${stderr || stdout || ""}\n` +
      `Run formatter setup first: cd ${FORMATTER_DIR} && python3 -m venv .venv && .venv/bin/python -m pip install -r requirements.txt`
    );
  }

  console.error(`${logPrefix} Rendered markdown via repo-local formatter (${theme}) -> ${outputPath}`);
  return outputPath;
}
