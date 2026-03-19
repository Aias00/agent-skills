import fs from "node:fs";
import path from "node:path";
import { spawnSync } from "node:child_process";
import { fileURLToPath } from "node:url";

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const SVG_RENDER_SCRIPT = path.join(__dirname, "render-svg-cover.py");

function isRemoteUrl(value: string): boolean {
  return /^https?:\/\//i.test(value);
}

function isSvgPath(value: string): boolean {
  return /\.svg$/i.test(value);
}

function getPngSiblingPath(svgPath: string): string {
  const parsed = path.parse(svgPath);
  return path.join(parsed.dir, `${parsed.name}.png`);
}

export function prepareWechatCoverPath(
  coverPath: string | undefined,
  options: { size?: string; logPrefix?: string } = {},
): string | undefined {
  if (!coverPath) return undefined;
  if (isRemoteUrl(coverPath)) return coverPath;
  if (!isSvgPath(coverPath)) return coverPath;

  const absoluteSvgPath = path.resolve(coverPath);
  if (!fs.existsSync(absoluteSvgPath)) return undefined;

  const outputPngPath = getPngSiblingPath(absoluteSvgPath);
  const svgStat = fs.statSync(absoluteSvgPath);
  const shouldRender =
    !fs.existsSync(outputPngPath) ||
    fs.statSync(outputPngPath).mtimeMs < svgStat.mtimeMs;

  if (!shouldRender) {
    return outputPngPath;
  }

  const logPrefix = options.logPrefix || "[wechat]";
  const args = [SVG_RENDER_SCRIPT, "--svg", absoluteSvgPath, "--out", outputPngPath];
  if (options.size) args.push("--size", options.size);

  console.error(`${logPrefix} Rendering SVG cover: ${absoluteSvgPath}`);
  const result = spawnSync("python3", args, {
    stdio: ["ignore", "pipe", "pipe"],
    encoding: "utf-8",
  });

  if (result.status !== 0) {
    const stderr = result.stderr?.trim();
    const stdout = result.stdout?.trim();
    throw new Error(stderr || stdout || "SVG cover render failed");
  }

  if (!fs.existsSync(outputPngPath)) {
    throw new Error(`Rendered cover missing: ${outputPngPath}`);
  }

  return outputPngPath;
}
