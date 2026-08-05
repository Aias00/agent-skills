import fs from "node:fs";
import path from "node:path";
import { spawnSync } from "node:child_process";

const SCRIPT_DIR = path.dirname(import.meta.path);
const REPO_ROOT = path.resolve(SCRIPT_DIR, "..", "..");
const FORMATTER_DIR = path.join(REPO_ROOT, "wechat-article-formatter");
const FORMATTER_SCRIPT = path.join(FORMATTER_DIR, "scripts", "markdown_to_html.py");
const FORMATTER_TEMPLATES_DIR = path.join(FORMATTER_DIR, "templates");
const FORMATTER_VENV_PYTHON = process.platform === "win32"
  ? path.join(FORMATTER_DIR, ".venv", "Scripts", "python.exe")
  : path.join(FORMATTER_DIR, ".venv", "bin", "python");

// Legacy theme aliases that predate the repo-local formatter; all map to the
// original default theme. Kept so old invocations keep working.
const LEGACY_THEME_ALIASES = new Set(["default", "grace", "simple", "modern"]);

/**
 * Discover available themes by reading the formatter's templates/ directory
 * (`<name>-theme.css` -> `<name>`). This stays in sync with whatever themes the
 * formatter actually ships, so passing any real theme works instead of being
 * silently downgraded to the default.
 *
 * Falls back to a minimal known set if the templates dir is unreadable (e.g.
 * running outside the repo layout), so the function never throws on lookup.
 */
function discoverAvailableThemes(): Set<string> {
  const themes = new Set<string>(["mist-blue", "ai-tech"]);
  try {
    if (!fs.existsSync(FORMATTER_TEMPLATES_DIR)) return themes;
    for (const entry of fs.readdirSync(FORMATTER_TEMPLATES_DIR)) {
      const match = entry.match(/^(.+)-theme\.css$/i);
      if (match) themes.add(match[1]!.toLowerCase());
    }
  } catch {
    // Non-fatal: callers fall back to the default theme on unknown input.
  }
  return themes;
}

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
  const available = discoverAvailableThemes();
  if (available.has(normalized)) return normalized;
  if (LEGACY_THEME_ALIASES.has(normalized)) {
    console.error(`${logPrefix} Legacy markdown theme "${normalized}" detected. Using "mist-blue" with the repo-local formatter.`);
    return "mist-blue";
  }
  console.error(`${logPrefix} Unknown markdown theme "${theme}". Available: ${[...available].sort().join(", ")}. Using "mist-blue" with the repo-local formatter.`);
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
  options: { theme?: string; outputPath?: string; logPrefix?: string; preserveExistingHtml?: boolean } = {},
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

  if (options.preserveExistingHtml && fs.existsSync(outputPath)) {
    console.error(`${logPrefix} Found existing themed HTML at ${outputPath}; skipping re-render. Pass --theme to force.`);
    return outputPath;
  }
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
