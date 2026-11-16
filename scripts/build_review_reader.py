"""Build a static, source-linked reader for the public synthetic VAD review packet.

Only the curated Markdown paths below and Markdown files in the public evidence
packet are read. This builder deliberately does not crawl the repository.
"""
from __future__ import annotations

from datetime import datetime, timezone
from hashlib import sha256
from html import escape
from pathlib import Path, PurePosixPath
import json
import re
import shutil
import sys
from urllib.parse import unquote, urlsplit

import markdown

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "site" / "review"
REPO_URL = "https://github.com/dedsec-terminal/Vendor-Assurance-Desk"
PAGES_URL = "https://dedsec-terminal.github.io/Vendor-Assurance-Desk"
CURATED = (
    ("docs/due_diligence_review.md", "Supplier due diligence review", "Assessment", True),
    ("docs/stakeholder_brief.md", "Decision brief", "Assessment", True),
    ("output/outcome_scorecard.md", "Outcome scorecard", "Results", False),
    ("docs/platform_integration.md", "GRC platform integration", "Platform", False),
    ("docs/native_framework_mapping.md", "Native ISO control references", "Platform", True),
    ("docs/demo_walkthrough.md", "Review walkthrough", "Guide", True),
    ("case-study/methodology.md", "Review methodology", "Methodology", True),
    ("case-study/questionnaire.md", "Assessment questionnaire", "Working papers", True),
    ("case-study/feedback_template.md", "Stakeholder feedback record", "Working papers", False),
)
PACKET_GLOB = "case-study/evidence-packet/*.md"


def slug(path: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", path.lower()).strip("-")


def collect_sources():
    records = []
    for rel, title, group, required in CURATED:
        path = ROOT / rel
        if path.is_file():
            records.append({"path": path, "rel": rel, "title": title, "group": group})
        elif required:
            raise FileNotFoundError(f"Required review source is missing: {rel}")
    for path in sorted((ROOT / "case-study" / "evidence-packet").glob("*.md"), key=lambda p: p.name.casefold()):
        rel = path.relative_to(ROOT).as_posix()
        records.append({"path": path, "rel": rel, "title": title_from_markdown(path), "group": "Evidence"})
    # Preserve stable order while preventing duplicate entries from future curated changes.
    unique = {}
    for record in records:
        unique.setdefault(record["rel"].casefold(), record)
    for record in unique.values():
        record["id"] = slug(record["rel"])
    return list(unique.values())


def title_from_markdown(path: Path) -> str:
    for line in path.read_text(encoding="utf-8-sig").splitlines():
        match = re.match(r"^#\s+(.+?)\s*#*\s*$", line)
        if match:
            return match.group(1)
    return path.stem.replace("_", " ").replace("-", " ").title()


def is_external(url: str) -> bool:
    return bool(urlsplit(url).scheme or url.startswith("//") or url.startswith("#"))


def rebase_links(source_rel: str, text: str, page_map: dict[str, str]) -> str:
    source_dir = PurePosixPath(source_rel).parent

    def replace(match):
        whole, label, url, tail = match
        decoded = unquote(url)
        if is_external(decoded) or decoded.startswith("mailto:"):
            return whole
        parts = urlsplit(decoded)
        target = (source_dir / parts.path).as_posix()
        # Normalize dot segments without permitting an escape out of repository.
        normalized = str(PurePosixPath(target))
        stack = []
        for part in normalized.split("/"):
            if part in ("", "."):
                continue
            if part == "..":
                if not stack:
                    return whole
                stack.pop()
            else:
                stack.append(part)
        repo_target = "/".join(stack)
        target_page = page_map.get(repo_target.casefold())
        if target_page:
            dest = target_page
        elif repo_target:
            dest = f"{REPO_URL}/blob/main/{repo_target}"
        else:
            return whole
        if parts.fragment:
            dest += "#" + parts.fragment
        if parts.query:
            dest += "?" + parts.query
        return f"[{label}]({dest}{tail}"

    # Keep Markdown's optional title suffix intact while rebasing its destination.
    return re.sub(r"(\[([^\]]*)\]\()([^\s)]+)([^)]*\))", lambda m: replace((m.group(0), m.group(2), m.group(3), m.group(4))), text)


def render_markdown(source_rel: str, text: str, page_map: dict[str, str]) -> str:
    prepared = rebase_links(source_rel, text, page_map)
    return markdown.markdown(
        prepared,
        extensions=["tables", "fenced_code", "toc", "sane_lists"],
        output_format="html5",
    )


def page_shell(title: str, content: str, active: str = "") -> str:
    return f'''<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<meta name="color-scheme" content="light"><meta name="description" content="Synthetic third-party risk assessment evidence and decision review packet.">
<meta http-equiv="Content-Security-Policy" content="default-src 'self' data:; img-src 'self' data:; style-src 'self' 'unsafe-inline'; script-src 'self'; object-src 'none'; base-uri 'none'; form-action 'self'">
<title>{escape(title)} | Vendor Assurance Desk</title><link rel="stylesheet" href="reader.css"></head>
<body><a class="skip" href="#main">Skip to content</a>{content}
<script src="reader.js" defer></script></body></html>'''


def sidebar(records, active=""):
    groups = {}
    for item in records:
        groups.setdefault(item["group"], []).append(item)
    nav = []
    for group, items in groups.items():
        links = "".join(
            f'<a class="nav-link{" active" if item["id"] == active else ""}" href="{escape(item["id"])}.html">{escape(item["title"])}</a>'
            for item in items
        )
        nav.append(f'<div class="nav-group"><div class="nav-heading">{escape(group)}</div>{links}</div>')
    return "".join(nav)


def build():
    records = collect_sources()
    OUT.mkdir(parents=True, exist_ok=True)
    # Remove only generated HTML from our own output directory; never recursively clear it.
    for old in OUT.glob("*.html"):
        old.unlink()
    for old in (OUT / "source-manifest.json", OUT / "search-index.json"):
        if old.exists():
            old.unlink()
    page_map = {r["rel"].casefold(): f'{r["id"]}.html' for r in records}
    manifest_sources = []
    search = []
    for item in records:
        raw = item["path"].read_bytes()
        text = raw.decode("utf-8-sig")
        # The page heading carries the document identity; omit the source file's
        # leading H1 to avoid displaying the same title twice.
        text = re.sub(r"\A\s*#\s+[^\r\n]+\s*(?:\r?\n)+", "", text, count=1)
        rendered = render_markdown(item["rel"], text, page_map)
        digest = sha256(raw).hexdigest()
        word_count = len(re.findall(r"\b[\w'-]+\b", re.sub(r"[`*_>#|]", " ", text)))
        source_path = f'{REPO_URL}/blob/main/{item["rel"]}'
        body = f'''<div class="layout"><aside class="sidebar" aria-label="Review documents"><a class="brand" href="index.html"><span class="brand-mark">VA</span><span>Vendor Assurance Desk<small>Evidence review packet</small></span></a><a class="back" href="../index.html">← Back to project</a><label class="search-label" for="search">Find a document</label><input id="search" type="search" placeholder="Search documents…" autocomplete="off" aria-controls="nav-list"><nav id="nav-list">{sidebar(records, item["id"])}</nav></aside><main id="main" class="article"><div class="eyebrow">{escape(item["group"])} <span>·</span> Synthetic case study</div><h1>{escape(item["title"])}</h1><div class="sourcebar"><span>Source: <a href="{escape(source_path)}">{escape(item["rel"])}</a></span><span>{word_count:,} words · SHA-256 <code>{digest[:16]}…</code></span></div><div class="provenance">Training fixture only. HarborPay Demo, evidence, dates, roles, and findings are fictional. This packet supports a simulated human review; it is not a real vendor decision or assurance opinion.</div><article class="markdown-body">{rendered}</article><footer><a href="index.html">Review packet index</a><span>Source hash recorded in <a href="source-manifest.json">manifest</a></span></footer></main></div>'''
        (OUT / f'{item["id"]}.html').write_text(page_shell(item["title"], body, item["id"]), encoding="utf-8")
        manifest_sources.append({"path": item["rel"], "page": f'{item["id"]}.html', "sha256": digest, "bytes": len(raw), "words": word_count})
        # Script-free JSON data: escape HTML delimiters to prevent accidental script break-out.
        plain = re.sub(r"[\s#*`|]+", " ", text).strip()
        search.append({"title": item["title"], "group": item["group"], "path": item["rel"], "page": f'{item["id"]}.html', "text": plain[:18000]})

    manifest = {"schema_version": 1, "generated_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"), "scope": "Explicit public Markdown review sources only; no recursive repository crawl.", "sources": manifest_sources}
    (OUT / "source-manifest.json").write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    (OUT / "search-index.json").write_text(json.dumps(search, ensure_ascii=False).replace("<", "\\u003c").replace(">", "\\u003e").replace("&", "\\u0026") + "\n", encoding="utf-8")

    cards = "".join(f'<a class="card" data-search-item href="{escape(i["id"])}.html"><span class="card-tag">{escape(i["group"])}</span><strong>{escape(i["title"])}</strong><span class="card-path">{escape(i["rel"])}</span><span class="arrow" aria-hidden="true">↗</span></a>' for i in records)
    index_body = f'''<div class="layout"><aside class="sidebar" aria-label="Review documents"><a class="brand" href="index.html"><span class="brand-mark">VA</span><span>Vendor Assurance Desk<small>Evidence review packet</small></span></a><a class="back" href="../index.html">← Back to project</a><label class="search-label" for="search">Find a document</label><input id="search" type="search" placeholder="Search documents…" autocomplete="off" aria-controls="nav-list"><nav id="nav-list">{sidebar(records)}</nav></aside><main id="main" class="article index-page"><div class="eyebrow">PUBLIC REVIEW PACKET <span>·</span> FICTIONAL CASE</div><h1>Supplier evidence review</h1><p class="dek">A source-linked working packet for reviewing a fictional payroll SaaS supplier, documenting uncertainty, and preparing a human decision.</p><div class="provenance prominent">All supplier, service, evidence, dates, roles, risk ratings and outcomes are synthetic. The materials demonstrate a repeatable review workflow; they are not real assurance evidence, a completed client engagement, or approval to onboard.</div><div class="index-tools"><span>{len(records)} curated documents</span><a href="source-manifest.json">Source hash manifest</a></div><div class="cards">{cards}</div><section class="how"><h2>How to use this packet</h2><ol><li>Start with the <a href="{page_map.get('docs/due_diligence_review.md','docs/due_diligence_review.md')}">supplier review</a> and follow every conclusion to its evidence item.</li><li>Use the methodology and questionnaire to separate missing, stale, out-of-scope and unverified evidence.</li><li>Read the decision brief and scorecard as simulated outputs. Only an authorized reviewer can accept risk or approve onboarding.</li><li>Use the feedback record after a real peer or mentor discussion; do not imply feedback occurred before it is recorded.</li></ol><p>Documents link to their reader pages where included and to the public repository source otherwise. Source hashes identify the exact Markdown inputs used for this build.</p></section><footer><a href="../index.html">← Project dashboard</a><span>Generated from curated public Markdown sources</span></footer></main></div>'''
    (OUT / "index.html").write_text(page_shell("Supplier evidence review", index_body), encoding="utf-8")
    write_assets()
    print(f"Review reader built: {OUT} ({len(records)} sources; Markdown {markdown.__version__})")
    return OUT


def write_assets():
    css = r'''*{box-sizing:border-box} :root{color-scheme:light;--ink:#182230;--muted:#617184;--line:#d9e0e8;--paper:#fff;--wash:#f4f7fa;--accent:#235c85;--accent-soft:#e9f2f8;--warning:#8a5a05;--warning-bg:#fff6df}html{scroll-behavior:smooth}body{margin:0;background:var(--wash);color:var(--ink);font:16px/1.62 Inter,"Segoe UI",Arial,sans-serif}.skip{position:absolute;left:-999px;top:1rem}.skip:focus{left:1rem;z-index:9;background:#fff;padding:.5rem}.layout{min-height:100vh;display:grid;grid-template-columns:278px minmax(0,1fr)}.sidebar{position:sticky;top:0;height:100vh;overflow:auto;background:#111d2b;color:#eff4f8;padding:26px 18px}.brand{display:flex;align-items:center;gap:11px;color:#fff;text-decoration:none;font-weight:700;line-height:1.25}.brand small{display:block;color:#a9bbc9;font-size:12px;font-weight:400;margin-top:3px}.brand-mark{display:grid;place-items:center;width:39px;height:39px;background:#d7e4ed;color:#122c40;border-radius:9px;font-size:13px;letter-spacing:.04em}.back{display:block;margin:28px 0 23px;padding:9px 10px;border:1px solid #354555;border-radius:7px;color:#dce8ef;text-decoration:none;font-size:14px}.search-label{display:block;font-size:12px;text-transform:uppercase;letter-spacing:.08em;color:#b7c4ce;margin:0 0 6px}input[type=search]{width:100%;padding:10px 11px;border:1px solid #536271;border-radius:7px;background:#1d2a37;color:#fff;font:inherit;font-size:14px}input::placeholder{color:#aebbc6}nav{margin-top:21px}.nav-group{margin-bottom:20px}.nav-heading{padding:0 9px 6px;color:#92a7b6;text-transform:uppercase;letter-spacing:.1em;font-size:10px;font-weight:700}.nav-link{display:block;padding:7px 9px;border-radius:6px;color:#dae4eb;text-decoration:none;font-size:13px;line-height:1.35}.nav-link:hover,.nav-link.active{background:#263a4c;color:#fff}.nav-link.active{box-shadow:inset 2px 0 #a7c9df}.article{width:min(100%,1000px);margin:0 auto;padding:50px clamp(24px,6vw,76px) 36px;background:var(--paper);min-height:100vh}.eyebrow{font-size:11px;letter-spacing:.13em;font-weight:750;color:var(--accent);text-transform:uppercase}.eyebrow span{color:#9eabb7;margin:0 5px}h1{font-size:clamp(30px,4vw,43px);line-height:1.13;letter-spacing:-.035em;margin:12px 0 13px}h2{font-size:25px;line-height:1.25;margin:2.1em 0 .7em;letter-spacing:-.02em}h3{font-size:19px;line-height:1.35;margin:1.7em 0 .45em}h4{font-size:16px;margin:1.5em 0 .4em}.dek{color:#455668;font-size:19px;line-height:1.52;max-width:720px;margin:0 0 22px}.sourcebar{display:flex;justify-content:space-between;gap:12px;flex-wrap:wrap;color:var(--muted);font-size:12px;border-bottom:1px solid var(--line);padding:6px 0 15px}.sourcebar a,.markdown-body a,.how a{color:#155b89;text-decoration-thickness:1px;text-underline-offset:3px}.sourcebar a:hover,.markdown-body a:hover{color:#0a395d}.sourcebar code{font-size:11px}.provenance{margin:20px 0 27px;padding:12px 15px;border-left:3px solid #c18a22;background:var(--warning-bg);color:#594715;font-size:13px;line-height:1.5}.prominent{font-size:14px;padding:15px 17px}.markdown-body{font-size:16px;overflow-wrap:anywhere}.markdown-body p{margin:.8em 0 1.05em}.markdown-body li{padding-left:4px;margin:.27em 0}.markdown-body ul,.markdown-body ol{padding-left:1.45em}.markdown-body table{border-collapse:collapse;width:100%;min-width:100%;display:block;overflow-x:auto;margin:1.25em 0 1.6em;font-size:14px}.markdown-body th,.markdown-body td{min-width:110px;border:1px solid #d8e0e7;padding:9px 11px;text-align:left;vertical-align:top;overflow-wrap:normal;word-break:normal}.markdown-body th:first-child,.markdown-body td:first-child{min-width:130px}.markdown-body th{background:#f0f4f7;font-weight:700}.markdown-body tr:nth-child(even) td{background:#fafbfd}.markdown-body blockquote{margin:1.3em 0;padding:4px 17px;border-left:3px solid #88a9be;color:#536476;background:#f7fafc}.markdown-body pre{white-space:pre;overflow:auto;padding:14px 16px;border:1px solid #dce3e9;border-radius:7px;background:#f5f7f9;font-size:13px;line-height:1.5}.markdown-body code{font-family:ui-monospace,SFMono-Regular,Consolas,monospace;font-size:.9em}.markdown-body :not(pre)>code{background:#f0f3f6;padding:2px 4px;border-radius:4px}.markdown-body hr{border:0;border-top:1px solid var(--line);margin:2em 0}.markdown-body img{max-width:100%;height:auto}.markdown-body a{overflow-wrap:anywhere}.toc{padding:14px 17px;margin:20px 0;background:#f6f8fa;border:1px solid #e1e6eb;border-radius:8px}.toc ul{margin:.3em 0}.index-tools{display:flex;justify-content:space-between;border-bottom:1px solid var(--line);padding:9px 0 13px;color:var(--muted);font-size:13px}.index-tools a{color:#155b89}.cards{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:12px;margin:19px 0 34px}.card{position:relative;display:flex;flex-direction:column;gap:7px;min-height:115px;padding:15px 39px 14px 15px;border:1px solid var(--line);border-radius:9px;color:var(--ink);text-decoration:none;background:#fff;transition:border-color .15s,transform .15s}.card:hover{border-color:#8aaabe;transform:translateY(-1px)}.card-tag{color:var(--accent);font-size:10px;text-transform:uppercase;letter-spacing:.1em;font-weight:750}.card strong{font-size:16px;line-height:1.35}.card-path{color:var(--muted);font:11px/1.35 ui-monospace,Consolas,monospace;overflow-wrap:anywhere}.arrow{position:absolute;right:15px;top:14px;color:#536b7c}.how{border-top:1px solid var(--line);padding-top:8px}.how ol{padding-left:22px}.how li{margin:9px 0}.how p{font-size:14px;color:#526274}footer{display:flex;justify-content:space-between;gap:15px;flex-wrap:wrap;border-top:1px solid var(--line);margin-top:40px;padding-top:14px;color:var(--muted);font-size:12px}footer a{color:#155b89}body.searching .nav-link.search-hidden,body.searching .card.search-hidden{display:none}body.searching .nav-group.search-hidden{display:none}@media(max-width:760px){.layout{display:block}.sidebar{position:relative;height:auto;max-height:none;padding:18px 16px}.back{display:inline-block;margin:13px 0}.sidebar nav{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:5px 12px;max-height:34vh;overflow:auto}.nav-group{margin:0 0 8px}.article{padding:29px 20px 27px;min-height:auto}.cards{grid-template-columns:1fr}.sourcebar{display:block}.sourcebar span{display:block;margin:3px 0}}@media(prefers-reduced-motion:reduce){html{scroll-behavior:auto}.card{transition:none}}'''
    js = r'''"use strict";
(()=>{const input=document.getElementById("search");if(!input)return;const links=[...document.querySelectorAll(".nav-link")],cards=[...document.querySelectorAll("[data-search-item]")];input.addEventListener("input",()=>{const q=input.value.trim().toLocaleLowerCase();document.body.classList.toggle("searching",Boolean(q));for(const el of [...links,...cards])el.classList.toggle("search-hidden",Boolean(q)&&!el.textContent.toLocaleLowerCase().includes(q));for(const group of document.querySelectorAll(".nav-group"))group.classList.toggle("search-hidden",!group.querySelector(".nav-link:not(.search-hidden)"));});})();'''
    (OUT / "reader.css").write_text(css + "\n", encoding="utf-8")
    (OUT / "reader.js").write_text(js + "\n", encoding="utf-8")


if __name__ == "__main__":
    try:
        build()
    except Exception as exc:
        print(f"Review reader build failed: {exc}", file=sys.stderr)
        raise
