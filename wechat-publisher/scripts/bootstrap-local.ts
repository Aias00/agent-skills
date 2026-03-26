#!/usr/bin/env bun

import fs from "node:fs";
import path from "node:path";
import process from "node:process";
import { spawnSync } from "node:child_process";
import { fileURLToPath } from "node:url";

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const SKILL_DIR = path.resolve(__dirname, "..");
const REPO_ROOT = path.resolve(SKILL_DIR, "..");
const FORMATTER_DIR = path.join(REPO_ROOT, "wechat-article-formatter");
const FORMATTER_REQUIREMENTS = path.join(FORMATTER_DIR, "requirements.txt");
const FORMATTER_VENV_PYTHON = process.platform === "win32"
  ? path.join(FORMATTER_DIR, ".venv", "Scripts", "python.exe")
  : path.join(FORMATTER_DIR, ".venv", "bin", "python");

interface Options {
  projectRoot: string;
  force: boolean;
  skipFormatterSetup: boolean;
}

function printUsage(): never {
  console.log(`
Bootstrap repo-local configuration for wechat-publisher.

Usage:
  bun scripts/bootstrap-local.ts [--project-root <path>] [--force] [--skip-formatter-setup]

Options:
  --project-root <path>   Target project root. Default: current working directory
  --force                 Overwrite existing copied files
  --skip-formatter-setup  Skip repo-local wechat-article-formatter Python setup
  -h, --help              Show help
`);
  process.exit(0);
}

function parseArgs(argv: string[]): Options {
  if (argv.includes("-h") || argv.includes("--help")) {
    printUsage();
  }

  const options: Options = {
    projectRoot: process.cwd(),
    force: false,
    skipFormatterSetup: false,
  };

  for (let i = 0; i < argv.length; i++) {
    const arg = argv[i];
    if (arg === "--project-root" && argv[i + 1]) {
      options.projectRoot = path.resolve(argv[++i]);
    } else if (arg === "--force") {
      options.force = true;
    } else if (arg === "--skip-formatter-setup") {
      options.skipFormatterSetup = true;
    } else {
      throw new Error(`Unknown argument: ${arg}`);
    }
  }

  return options;
}

function ensureDir(dirPath: string): void {
  fs.mkdirSync(dirPath, { recursive: true });
}

function copyTemplate(src: string, dest: string, force: boolean): "created" | "skipped" | "overwritten" {
  const existed = fs.existsSync(dest);
  if (existed && !force) {
    return "skipped";
  }
  ensureDir(path.dirname(dest));
  fs.copyFileSync(src, dest);
  return existed ? "overwritten" : "created";
}

function logResult(label: string, dest: string, status: "created" | "skipped" | "overwritten"): void {
  const icon = status === "skipped" ? "↷" : "✅";
  console.log(`${icon} ${label}: ${dest} (${status})`);
}

function resolveSystemPython(): string | undefined {
  for (const candidate of ["python3", "python"]) {
    const result = spawnSync(candidate, ["--version"], { stdio: "pipe", encoding: "utf-8" });
    if (result.status === 0) return candidate;
  }
  return undefined;
}

function runOrThrow(command: string, args: string[], cwd: string, label: string): void {
  const result = spawnSync(command, args, {
    cwd,
    stdio: "pipe",
    encoding: "utf-8",
  });
  if (result.status !== 0) {
    const stderr = result.stderr?.trim();
    const stdout = result.stdout?.trim();
    throw new Error(`${label} failed.\n${stderr || stdout || ""}`);
  }
}

function ensurePreferredFormatterRuntime(): void {
  if (!fs.existsSync(FORMATTER_REQUIREMENTS)) {
    throw new Error(`Formatter requirements not found: ${FORMATTER_REQUIREMENTS}`);
  }

  const pythonBin = resolveSystemPython();
  if (!pythonBin) {
    throw new Error("Python not found. Install python3/python before bootstrapping the formatter runtime.");
  }

  if (!fs.existsSync(FORMATTER_VENV_PYTHON)) {
    console.log(`✅ Preferred formatter venv: creating ${FORMATTER_VENV_PYTHON}`);
    runOrThrow(pythonBin, ["-m", "venv", path.join(FORMATTER_DIR, ".venv")], FORMATTER_DIR, "Create formatter venv");
  } else {
    console.log(`↷ Preferred formatter venv: ${FORMATTER_VENV_PYTHON} (exists)`);
  }

  runOrThrow(FORMATTER_VENV_PYTHON, ["-m", "pip", "install", "-r", FORMATTER_REQUIREMENTS], FORMATTER_DIR, "Install formatter requirements");
  console.log(`✅ Preferred formatter deps: ${FORMATTER_REQUIREMENTS}`);
}

function main(): void {
  const options = parseArgs(process.argv.slice(2));
  const projectRoot = options.projectRoot;
  const projectBaoyuDir = path.join(projectRoot, ".baoyu-skills");
  const projectWechatDir = path.join(projectBaoyuDir, "wechat-publisher");

  const extendTemplate = path.join(SKILL_DIR, "EXTEND.md.example");
  const envTemplate = path.join(SKILL_DIR, ".env.example");

  const extendDest = path.join(projectWechatDir, "EXTEND.md");
  const envExampleDest = path.join(projectBaoyuDir, ".env.example");

  ensureDir(projectWechatDir);

  const extendStatus = copyTemplate(extendTemplate, extendDest, options.force);
  logResult("Project EXTEND", extendDest, extendStatus);

  const envStatus = copyTemplate(envTemplate, envExampleDest, options.force);
  logResult("Project .env example", envExampleDest, envStatus);

  if (!options.skipFormatterSetup) {
    ensurePreferredFormatterRuntime();
  } else {
    console.log("↷ Preferred formatter deps: skipped by --skip-formatter-setup");
  }

  console.log("\nNext steps:");
  console.log(`1. Edit ${extendDest}`);
  console.log(`2. Copy ${envExampleDest} -> ${path.join(projectBaoyuDir, ".env")} and fill real credentials if you plan to use API publish`);
  console.log(`3. Run: (cd ${SKILL_DIR} && bun scripts/check-permissions.ts --project-root ${projectRoot})`);
  console.log(`4. Dry-run publish: (cd ${SKILL_DIR} && bun scripts/wechat-publish.ts <article.md> --dry-run)`);
}

try {
  main();
} catch (error) {
  console.error(error instanceof Error ? error.message : String(error));
  process.exit(1);
}
