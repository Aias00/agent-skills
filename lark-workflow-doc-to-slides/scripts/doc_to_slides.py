#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path
from urllib.parse import urlparse
from xml.sax.saxutils import escape


VALID_LAYOUTS = {
    "title-only",
    "title-body",
    "two-column",
    "bullets",
    "comparison",
    "timeline",
    "metrics",
}
TARGET_MODES = {"new", "append"}
CONTENT_MODES = {"faithful", "report"}
FETCHABLE_ENTITY_TYPES = {"DOC", "DOCX"}
RESOLVABLE_ENTITY_TYPES = {"WIKI"}
FETCHABLE_WIKI_OBJECT_TYPES = {"doc", "docx"}
SML_NS = "http://www.larkoffice.com/sml/2.0"
HTML_TAG_RE = re.compile(r"<[^>]+>")


class PublishError(RuntimeError):
    def __init__(self, message: str, result: dict) -> None:
        super().__init__(message)
        self.result = result


def emit_error(command: str, error: Exception) -> int:
    payload = {
        "ok": False,
        "command": command,
        "error": str(error),
        "error_type": type(error).__name__,
    }
    json.dump(payload, sys.stdout, ensure_ascii=False, indent=2)
    sys.stdout.write("\n")
    return 1


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Resolve, fetch, validate, render, and publish doc-to-slides workflow artifacts."
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    resolve = subparsers.add_parser("resolve-source")
    resolve.add_argument("--doc-url")
    resolve.add_argument("--doc-token")
    resolve.add_argument("--doc-name")
    resolve.add_argument("--run-dir", required=True)

    fetch = subparsers.add_parser("fetch")
    fetch.add_argument("--resolved-source", required=True)
    fetch.add_argument("--run-dir", required=True)

    validate = subparsers.add_parser("validate-outline")
    validate.add_argument("--outline", required=True)

    render = subparsers.add_parser("render")
    render.add_argument("--outline", required=True)
    render.add_argument("--run-dir", required=True)

    publish = subparsers.add_parser("publish")
    publish.add_argument("--outline", required=True)
    publish.add_argument("--slides-json", required=True)
    publish.add_argument("--run-dir", required=True)
    publish.add_argument("--target-slides-url")

    return parser.parse_args(argv)


def ensure_run_dir(path_arg: str | None) -> Path:
    if not path_arg:
        raise ValueError("run directory is required")
    run_dir = Path(path_arg)
    run_dir.mkdir(parents=True, exist_ok=True)
    return run_dir


def write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def read_json(path: Path) -> object:
    return json.loads(path.read_text(encoding="utf-8"))


def run_lark_cli(args: list[str]) -> dict:
    proc = subprocess.run(args, capture_output=True, text=True, check=False)
    if proc.returncode != 0:
        message = proc.stderr.strip() or proc.stdout.strip() or f"lark-cli failed: {' '.join(args)}"
        raise RuntimeError(message)
    try:
        return json.loads(proc.stdout)
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"lark-cli returned invalid JSON: {exc}") from exc


def normalize_entity_type(value: object) -> str:
    if isinstance(value, list):
        for item in value:
            normalized = normalize_entity_type(item)
            if normalized:
                return normalized
        return ""
    if value is None:
        return ""
    return str(value).strip().upper()


def strip_markup(text: object) -> str:
    if text is None:
        return ""
    return HTML_TAG_RE.sub("", str(text))


def stable_json_dumps(payload: object) -> str:
    return json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def fingerprint_payload(payload: object) -> str:
    return hashlib.sha256(stable_json_dumps(payload).encode("utf-8")).hexdigest()


def extract_search_results(search_result: dict) -> list[dict]:
    data = search_result.get("data")
    if isinstance(data, dict):
        return data.get("results") or data.get("res_units") or []
    return search_result.get("results") or search_result.get("res_units") or []


def extract_fetch_payload(raw: dict) -> dict:
    data = raw.get("data")
    if isinstance(data, dict) and (
        "markdown" in data or "title" in data or "has_more" in data or "next_offset" in data
    ):
        return data
    return raw


def extract_search_candidates(search_result: dict) -> list[dict]:
    candidates: list[dict] = []
    for item in extract_search_results(search_result):
        result_meta = item.get("result_meta") or {}
        entity_type = normalize_entity_type(item.get("entity_type") or result_meta.get("doc_types"))
        url = result_meta.get("url") or item.get("url")
        if not url:
            continue
        if entity_type in FETCHABLE_ENTITY_TYPES:
            resolved_kind = "doc_url"
        elif entity_type in RESOLVABLE_ENTITY_TYPES:
            resolved_kind = "wiki_url"
        else:
            continue
        candidates.append(
            {
                "title": strip_markup(item.get("title") or item.get("title_highlighted") or result_meta.get("title") or ""),
                "resolved_kind": resolved_kind,
                "resolved_value": url,
                "entity_type": entity_type,
            }
        )
    return candidates


def extract_token(value: str) -> str:
    parsed = urlparse(value)
    if parsed.scheme:
        return parsed.path.rstrip("/").split("/")[-1]
    return value.rstrip("/").split("/")[-1]


def is_wiki_reference(value: str) -> bool:
    return "/wiki/" in value


def extract_wiki_node(payload: dict) -> dict:
    node = payload.get("node")
    if not isinstance(node, dict):
        raise RuntimeError("unexpected wiki get_node response shape")
    return node


def resolve_source(args: argparse.Namespace, run_dir: Path) -> dict:
    if args.doc_url:
        resolved = {
            "input_kind": "doc_url",
            "resolved_kind": "wiki_url" if is_wiki_reference(args.doc_url) else "doc_url",
            "resolved_value": args.doc_url,
            "title": "",
            "search_candidates": [],
            "needs_user_choice": False,
        }
    elif args.doc_token:
        resolved = {
            "input_kind": "doc_token",
            "resolved_kind": "doc_token",
            "resolved_value": args.doc_token,
            "title": "",
            "search_candidates": [],
            "needs_user_choice": False,
        }
    elif args.doc_name:
        search_result = run_lark_cli(
            [
                "lark-cli",
                "docs",
                "+search",
                "--as",
                "user",
                "--format",
                "json",
                "--query",
                args.doc_name,
            ]
        )
        candidates = extract_search_candidates(search_result)
        if not candidates:
            raise RuntimeError(f"no document found for name: {args.doc_name}")
        if len(candidates) == 1:
            resolved = {
                "input_kind": "doc_name",
                **candidates[0],
                "search_candidates": candidates,
                "needs_user_choice": False,
            }
        else:
            resolved = {
                "input_kind": "doc_name",
                "resolved_kind": "",
                "resolved_value": "",
                "title": "",
                "search_candidates": candidates,
                "needs_user_choice": True,
            }
    else:
        raise RuntimeError("one of --doc-url, --doc-token, or --doc-name is required")

    write_json(run_dir / "resolved-source.json", resolved)
    return resolved


def resolve_fetch_target(resolved: dict) -> tuple[str, dict | None]:
    fetch_target = resolved["resolved_value"]
    wiki_node: dict | None = None

    if resolved.get("resolved_kind") == "wiki_url" or is_wiki_reference(fetch_target):
        wiki_token = extract_token(fetch_target)
        node_result = run_lark_cli(
            [
                "lark-cli",
                "wiki",
                "spaces",
                "get_node",
                "--as",
                "user",
                "--params",
                json.dumps({"token": wiki_token}, ensure_ascii=False),
                "--format",
                "json",
            ]
        )
        wiki_node = extract_wiki_node(node_result)
        obj_type = str(wiki_node.get("obj_type") or "").lower()
        if obj_type not in FETCHABLE_WIKI_OBJECT_TYPES:
            raise RuntimeError(f"wiki source resolves to unsupported obj_type: {wiki_node.get('obj_type')}")
        obj_token = wiki_node.get("obj_token")
        if not obj_token:
            raise RuntimeError("wiki source did not include obj_token")
        fetch_target = obj_token

    return fetch_target, wiki_node


def ensure_resolved_source_ready(resolved: dict) -> None:
    if resolved.get("needs_user_choice"):
        raise RuntimeError("resolved source still requires explicit user choice before fetch")
    if not resolved.get("resolved_kind"):
        raise RuntimeError("resolved source is missing resolved_kind")
    if not resolved.get("resolved_value"):
        raise RuntimeError("resolved source is missing resolved_value")


def fetch_source(resolved: dict, run_dir: Path) -> dict:
    ensure_resolved_source_ready(resolved)
    offset = 0
    limit = 200
    pages: list[dict] = []
    markdown_parts: list[str] = []
    title = resolved.get("title") or ""
    fetch_target, wiki_node = resolve_fetch_target(resolved)

    while True:
        raw_page = run_lark_cli(
            [
                "lark-cli",
                "docs",
                "+fetch",
                "--as",
                "user",
                "--format",
                "json",
                "--doc",
                fetch_target,
                "--offset",
                str(offset),
                "--limit",
                str(limit),
            ]
        )
        page = extract_fetch_payload(raw_page)
        pages.append(raw_page)
        if page.get("title") and not title:
            title = page["title"]
        markdown = page.get("markdown", "")
        if markdown:
            markdown_parts.append(markdown.rstrip())
        if not page.get("has_more"):
            break
        offset = int(page.get("next_offset", offset + limit))

    result = {
        "title": title or (wiki_node.get("title") if wiki_node else ""),
        "markdown": "\n\n".join(part for part in markdown_parts if part),
        "pages": len(pages),
        "raw_pages": pages,
        "resolved_fetch_target": fetch_target,
    }
    if wiki_node:
        result["wiki_node"] = wiki_node

    write_json(run_dir / "source.json", result)
    (run_dir / "source.md").write_text(
        result["markdown"] + ("\n" if result["markdown"] else ""),
        encoding="utf-8",
    )
    return result


def validate_outline(outline: dict) -> None:
    presentation = outline.get("presentation")
    if not isinstance(presentation, dict):
        raise ValueError("missing presentation")
    source = presentation.get("source")
    if not isinstance(source, dict):
        raise ValueError("missing presentation.source")
    slides = outline.get("slides")
    if not isinstance(slides, list) or not slides:
        raise ValueError("slides must be a non-empty list")

    for field in ("title", "target_mode", "content_mode"):
        if not presentation.get(field):
            raise ValueError(f"missing presentation.{field}")
    if presentation["target_mode"] not in TARGET_MODES:
        raise ValueError(f"invalid presentation.target_mode: {presentation['target_mode']}")
    if presentation["content_mode"] not in CONTENT_MODES:
        raise ValueError(f"invalid presentation.content_mode: {presentation['content_mode']}")

    for field in ("input_kind", "resolved_kind", "resolved_value"):
        if not source.get(field):
            raise ValueError(f"missing presentation.source.{field}")

    for index, slide in enumerate(slides, start=1):
        for field in ("no", "role", "section_divider", "title", "layout", "key_points"):
            if field not in slide:
                raise ValueError(f"slide {index} missing {field}")
        if not isinstance(slide["no"], int) or slide["no"] <= 0:
            raise ValueError(f"slide {index} no must be a positive integer")
        if slide["layout"] not in VALID_LAYOUTS:
            raise ValueError(f"slide {index} invalid layout: {slide['layout']}")
        if not isinstance(slide["key_points"], list):
            raise ValueError(f"slide {index} key_points must be a list")
        if len(slide["key_points"]) > 5:
            raise ValueError(f"slide {index} exceeds 5 key points")
        if not isinstance(slide["section_divider"], bool):
            raise ValueError(f"slide {index} section_divider must be a boolean")

    if presentation["target_mode"] == "append":
        first_slide = slides[0]
        if first_slide.get("role") == "cover" and not bool(first_slide.get("section_divider")):
            raise ValueError("append mode cannot inject a generic cover slide")


def text_shape(x: int, y: int, width: int, height: int, text_type: str, inner_xml: str) -> str:
    return (
        f'<shape type="text" topLeftX="{x}" topLeftY="{y}" width="{width}" height="{height}">'
        f'<content textType="{text_type}">{inner_xml}</content>'
        "</shape>"
    )


def rect_shape(x: int, y: int, width: int, height: int, fill_color: str) -> str:
    return (
        f'<shape type="rect" topLeftX="{x}" topLeftY="{y}" width="{width}" height="{height}">'
        f'<fill><fillColor color="{fill_color}"/></fill>'
        f'<border color="rgb(203,213,225)" width="2"/>'
        "</shape>"
    )


def centered_text_shape(x: int, y: int, width: int, height: int, text: str, font_size: int = 18) -> str:
    return text_shape(
        x,
        y,
        width,
        height,
        "body",
        f'<p textAlign="center"><span color="rgb(51,65,85)" fontSize="{font_size}">{escape(text)}</span></p>',
    )


def title_paragraph(text: str) -> str:
    return f"<p>{escape(text)}</p>"


def bullets_xml(points: list[str]) -> str:
    if not points:
        return "<p></p>"
    return "".join(f"<ul><li><p>{escape(point)}</p></li></ul>" for point in points)


def wrap_slide(data_xml: str, note_text: str = "") -> str:
    note_xml = ""
    if note_text:
        note_xml = f'<note><content textType="body"><p>{escape(note_text)}</p></content></note>'
    return (
        f'<slide xmlns="{SML_NS}">'
        '<style><fill><fillColor color="rgb(248,250,252)"/></fill></style>'
        f"<data>{data_xml}</data>"
        f"{note_xml}"
        "</slide>"
    )


def split_points(points: list[str]) -> tuple[list[str], list[str]]:
    midpoint = max(1, (len(points) + 1) // 2)
    return points[:midpoint], points[midpoint:]


def render_title_only_slide(slide: dict) -> str:
    subtitle = slide.get("objective") or (slide.get("key_points") or [""])[0]
    data_xml = [
        text_shape(96, 96, 768, 110, "title", title_paragraph(slide["title"])),
    ]
    if subtitle:
        data_xml.append(text_shape(96, 220, 768, 120, "body", title_paragraph(subtitle)))
    return wrap_slide("".join(data_xml), slide.get("notes", ""))


def render_title_body_slide(slide: dict) -> str:
    data_xml = (
        text_shape(80, 72, 800, 80, "title", title_paragraph(slide["title"]))
        + text_shape(80, 170, 800, 280, "body", bullets_xml(slide.get("key_points", [])))
    )
    return wrap_slide(data_xml, slide.get("notes", ""))


def render_two_column_slide(slide: dict) -> str:
    left_points, right_points = split_points(slide.get("key_points", []))
    data_xml = (
        text_shape(80, 72, 800, 80, "title", title_paragraph(slide["title"]))
        + text_shape(80, 170, 360, 260, "body", bullets_xml(left_points))
        + text_shape(520, 170, 360, 260, "body", bullets_xml(right_points))
    )
    return wrap_slide(data_xml, slide.get("notes", ""))


def render_comparison_slide(slide: dict) -> str:
    labels = slide.get("source_sections") or ["方案 A", "方案 B"]
    left_label = labels[0] if len(labels) > 0 else "方案 A"
    right_label = labels[1] if len(labels) > 1 else "方案 B"
    left_points, right_points = split_points(slide.get("key_points", []))
    data_xml = (
        text_shape(80, 72, 800, 80, "title", title_paragraph(slide["title"]))
        + text_shape(80, 158, 360, 40, "body", title_paragraph(left_label))
        + text_shape(520, 158, 360, 40, "body", title_paragraph(right_label))
        + text_shape(80, 210, 360, 220, "body", bullets_xml(left_points))
        + text_shape(520, 210, 360, 220, "body", bullets_xml(right_points))
    )
    return wrap_slide(data_xml, slide.get("notes", ""))


def render_timeline_slide(slide: dict) -> str:
    items = []
    base_y = 170
    for index, point in enumerate(slide.get("key_points", [])):
        y = base_y + index * 62
        items.append(rect_shape(100, y, 760, 44, "rgb(226,232,240)"))
        items.append(centered_text_shape(120, y + 8, 720, 28, point, font_size=16))
    data_xml = text_shape(80, 72, 800, 80, "title", title_paragraph(slide["title"])) + "".join(items)
    return wrap_slide(data_xml, slide.get("notes", ""))


def render_metrics_slide(slide: dict) -> str:
    cards = []
    for index, point in enumerate(slide.get("key_points", [])):
        row = index // 3
        col = index % 3
        x = 80 + col * 260
        y = 180 + row * 120
        cards.append(rect_shape(x, y, 220, 88, "rgb(219,234,254)"))
        cards.append(centered_text_shape(x + 10, y + 28, 200, 32, point, font_size=18))
    data_xml = text_shape(80, 72, 800, 80, "title", title_paragraph(slide["title"])) + "".join(cards)
    return wrap_slide(data_xml, slide.get("notes", ""))


RENDERERS = {
    "title-only": render_title_only_slide,
    "title-body": render_title_body_slide,
    "two-column": render_two_column_slide,
    "bullets": render_title_body_slide,
    "comparison": render_comparison_slide,
    "timeline": render_timeline_slide,
    "metrics": render_metrics_slide,
}


def render_outline(outline: dict, run_dir: Path) -> dict:
    validate_outline(outline)
    rendered = []
    for slide in outline["slides"]:
        renderer = RENDERERS.get(slide["layout"])
        if renderer is None:
            raise ValueError(f"unsupported render layout: {slide['layout']}")
        rendered.append(renderer(slide))

    outline_fingerprint = fingerprint_payload(outline)
    slides_fingerprint = fingerprint_payload(rendered)
    result = {"slides": rendered, "count": len(rendered)}
    write_json(
        run_dir / "render-summary.json",
        {
            "count": len(rendered),
            "layouts": [s["layout"] for s in outline["slides"]],
            "outline_fingerprint": outline_fingerprint,
            "slides_fingerprint": slides_fingerprint,
        },
    )
    write_json(run_dir / "slides.json", rendered)
    return result


def extract_create_payload(raw: dict) -> dict:
    data = raw.get("data")
    if isinstance(data, dict) and data.get("xml_presentation_id"):
        return data
    if raw.get("xml_presentation_id"):
        return raw
    raise RuntimeError("unexpected slides +create response shape")


def extract_slide_create_payload(raw: dict) -> dict:
    if raw.get("slide_id"):
        return raw
    data = raw.get("data")
    if isinstance(data, dict) and data.get("slide_id"):
        return data
    raise RuntimeError("unexpected xml_presentation.slide create response shape")


def normalize_publish_result(
    target_mode: str,
    xml_presentation_id: str,
    url: str | None,
    slide_ids: list[str],
    run_dir: Path,
) -> dict:
    return {
        "target_mode": target_mode,
        "xml_presentation_id": xml_presentation_id,
        "url": url,
        "slide_ids": slide_ids,
        "slides_added": len(slide_ids),
        "run_dir": str(run_dir),
    }


def ensure_render_consistency(outline: dict, slides: list[str], run_dir: Path) -> None:
    summary_path = run_dir / "render-summary.json"
    if not summary_path.exists():
        raise RuntimeError("render-summary.json is required before publish")
    summary = read_json(summary_path)
    if not isinstance(summary, dict):
        raise RuntimeError("render-summary.json must be a JSON object")
    if summary.get("count") != len(slides):
        raise RuntimeError("slides.json does not match render-summary count")
    if summary.get("outline_fingerprint") != fingerprint_payload(outline):
        raise RuntimeError("outline.json no longer matches the rendered slides; rerun render")
    if summary.get("slides_fingerprint") != fingerprint_payload(slides):
        raise RuntimeError("slides.json no longer matches render-summary; rerun render")


def resolve_target_slides_url(target_slides_url: str) -> tuple[str, str | None]:
    if "/slides/" in target_slides_url:
        return extract_token(target_slides_url), target_slides_url
    if "/wiki/" in target_slides_url:
        wiki_token = extract_token(target_slides_url)
        raw = run_lark_cli(
            [
                "lark-cli",
                "wiki",
                "spaces",
                "get_node",
                "--as",
                "user",
                "--params",
                json.dumps({"token": wiki_token}, ensure_ascii=False),
                "--format",
                "json",
            ]
        )
        node = extract_wiki_node(raw)
        if node.get("obj_type") != "slides":
            raise RuntimeError("target wiki node is not a slides presentation")
        obj_token = node.get("obj_token")
        if not obj_token:
            raise RuntimeError("target wiki node did not include obj_token")
        return obj_token, target_slides_url
    raise RuntimeError("unsupported target_slides_url")


def create_slide_in_presentation(presentation_id: str, slide_xml: str) -> str:
    raw = run_lark_cli(
        [
            "lark-cli",
            "slides",
            "xml_presentation.slide",
            "create",
            "--as",
            "user",
            "--params",
            json.dumps({"xml_presentation_id": presentation_id}, ensure_ascii=False),
            "--data",
            json.dumps({"slide": {"content": slide_xml}}, ensure_ascii=False),
            "--format",
            "json",
        ]
    )
    return str(extract_slide_create_payload(raw)["slide_id"])


def publish_new_deck(title: str, slides: list[str], run_dir: Path) -> dict:
    create_raw = run_lark_cli(
        [
            "lark-cli",
            "slides",
            "+create",
            "--as",
            "user",
            "--title",
            title,
        ]
    )
    payload = extract_create_payload(create_raw)
    presentation_id = str(payload["xml_presentation_id"])
    url = payload.get("url")
    slide_ids: list[str] = []
    try:
        for slide_xml in slides:
            slide_ids.append(create_slide_in_presentation(presentation_id, slide_xml))
    except Exception as exc:
        raise PublishError(
            f"publish failed after {len(slide_ids)} slides: {exc}",
            normalize_publish_result("new", presentation_id, url, slide_ids, run_dir),
        ) from exc

    return normalize_publish_result("new", presentation_id, url, slide_ids, run_dir)


def publish_append(target_slides_url: str, slides: list[str], run_dir: Path) -> dict:
    presentation_id, url = resolve_target_slides_url(target_slides_url)
    slide_ids: list[str] = []
    try:
        for slide_xml in slides:
            slide_ids.append(create_slide_in_presentation(presentation_id, slide_xml))
    except Exception as exc:
        raise PublishError(
            f"append failed after {len(slide_ids)} slides: {exc}",
            normalize_publish_result("append", presentation_id, url, slide_ids, run_dir),
        ) from exc
    return normalize_publish_result("append", presentation_id, url, slide_ids, run_dir)


def publish_slides(outline: dict, slides: list[str], run_dir: Path, target_slides_url: str | None) -> dict:
    validate_outline(outline)
    ensure_render_consistency(outline, slides, run_dir)
    target_mode = outline["presentation"]["target_mode"]
    try:
        if target_mode == "new":
            result = publish_new_deck(outline["presentation"]["title"], slides, run_dir)
        elif target_mode == "append":
            if not target_slides_url:
                raise RuntimeError("target_slides_url is required for append mode")
            result = publish_append(target_slides_url, slides, run_dir)
        else:
            raise RuntimeError(f"unsupported target_mode: {target_mode}")
    except PublishError as exc:
        write_json(run_dir / "publish-result.json", exc.result)
        raise

    write_json(run_dir / "publish-result.json", result)
    return result


def load_slides_json(path: Path) -> list[str]:
    payload = read_json(path)
    if not isinstance(payload, list):
        raise ValueError("slides-json must contain a JSON array of slide XML strings")
    if not all(isinstance(item, str) for item in payload):
        raise ValueError("slides-json entries must be strings")
    return payload


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)

    if args.command == "resolve-source":
        sources = [value for value in (args.doc_url, args.doc_token, args.doc_name) if value]
        if len(sources) != 1:
            raise SystemExit(2)
        resolve_source(args, ensure_run_dir(args.run_dir))
        return 0

    if args.command == "fetch":
        run_dir = ensure_run_dir(args.run_dir)
        resolved = read_json(Path(args.resolved_source))
        if not isinstance(resolved, dict):
            raise ValueError("resolved-source must be a JSON object")
        fetch_source(resolved, run_dir)
        return 0

    if args.command == "validate-outline":
        try:
            outline = read_json(Path(args.outline))
            if not isinstance(outline, dict):
                raise ValueError("outline must be a JSON object")
            validate_outline(outline)
            return 0
        except (ValueError, RuntimeError, json.JSONDecodeError) as exc:
            return emit_error("validate-outline", exc)

    if args.command == "render":
        run_dir = ensure_run_dir(args.run_dir)
        outline = read_json(Path(args.outline))
        if not isinstance(outline, dict):
            raise ValueError("outline must be a JSON object")
        render_outline(outline, run_dir)
        return 0

    if args.command == "publish":
        run_dir = ensure_run_dir(args.run_dir)
        outline = read_json(Path(args.outline))
        if not isinstance(outline, dict):
            raise ValueError("outline must be a JSON object")
        slides = load_slides_json(Path(args.slides_json))
        publish_slides(outline, slides, run_dir, args.target_slides_url)
        return 0

    raise RuntimeError(f"unsupported command: {args.command}")


if __name__ == "__main__":
    raise SystemExit(main())
