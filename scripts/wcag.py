#!/usr/bin/env python3
"""Generate and check the WCAG references bundled in skills/ep-a11y.

Modes:
  update            fetch W3C's wcag.json and regenerate references/wcag/
  update --dry-run  report added, removed, and changed criteria; write nothing
  check             offline: generated files match the manifest, the index and
                    sc/ files agree, and checks.md / audit.md cite only
                    criteria that exist and are not obsolete

Standard library only. The WCAG version is the VERSION setting below.
"""

import argparse
import datetime
import hashlib
import json
import os
import re
import shutil
import sys
import tempfile
import urllib.request
from html.parser import HTMLParser
from pathlib import Path

VERSION = "22"
SOURCE_URL = "https://www.w3.org/WAI/WCAG{ver}/wcag.json"
TR_URL = "https://www.w3.org/TR/WCAG{ver}/"
UNDERSTANDING_URL = "https://www.w3.org/WAI/WCAG{ver}/Understanding/{id}.html"
LICENSE_URL = "https://www.w3.org/copyright/document-license-2023/"

REPO = Path(__file__).resolve().parent.parent
DEFAULT_OUT = REPO / "skills" / "ep-a11y" / "references" / "wcag"
GUIDANCE_FILES = ("checks.md", "audit.md")
GENERATOR = "scripts/wcag.py"
LEVELS = ("", "A", "AA", "AAA")


class SourceError(Exception):
    pass


def dotted(ver):
    return ".".join(ver) if ver.isdigit() else ver


# ---------------------------------------------------------------- HTML -> MD

VOID = {"br", "img", "hr", "input", "meta", "link", "wbr"}
BLOCK = {"p", "div", "ul", "ol", "li", "dl", "dt", "dd", "blockquote",
         "section", "table", "tr", "td", "th", "thead", "tbody", "pre",
         "h1", "h2", "h3", "h4", "h5", "h6", "figure", "figcaption"}


class Node:
    def __init__(self, tag, attrs=None, parent=None):
        self.tag = tag
        self.attrs = dict(attrs or [])
        self.parent = parent
        self.children = []


class TreeBuilder(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.root = Node("root")
        self.cur = self.root

    def handle_starttag(self, tag, attrs):
        node = Node(tag, attrs, self.cur)
        self.cur.children.append(node)
        if tag not in VOID:
            self.cur = node

    def handle_startendtag(self, tag, attrs):
        self.cur.children.append(Node(tag, attrs, self.cur))

    def handle_endtag(self, tag):
        n = self.cur
        while n is not self.root and n.tag != tag:
            n = n.parent
        if n is not self.root:
            self.cur = n.parent

    def handle_data(self, data):
        self.cur.children.append(data)


def parse_html(text):
    b = TreeBuilder()
    b.feed(text or "")
    b.close()
    return b.root


def collapse(s):
    return re.sub(r"\s+", " ", s)


class Converter:
    """Small HTML-to-Markdown converter for the markup used in wcag.json.

    Unknown tags fall back to their text content rather than being dropped.
    """

    def __init__(self, tr_base):
        self.tr_base = tr_base

    def href(self, h):
        h = (h or "").strip()
        if h.startswith("#"):
            return self.tr_base + h
        return h

    def inline(self, node):
        if isinstance(node, str):
            return collapse(node)
        tag = node.tag
        if tag == "br":
            return "\n"
        inner = "".join(self.inline(c) for c in node.children)
        if tag == "a" and node.attrs.get("href"):
            text = inner.strip()
            return f"[{text}]({self.href(node.attrs['href'])})" if text else ""
        if tag in ("em", "i", "cite"):
            return f"*{inner.strip()}*" if inner.strip() else inner
        if tag in ("strong", "b"):
            return f"**{inner.strip()}**" if inner.strip() else inner
        if tag == "code":
            return f"`{inner.strip()}`"
        return inner

    def para(self, nodes):
        text = "".join(self.inline(n) for n in nodes)
        lines = [collapse(l).strip() for l in text.split("\n")]
        return "\n".join(l for l in lines if l)

    def blocks(self, children):
        out, run = [], []

        def flush():
            if run:
                p = self.para(run)
                if p:
                    out.append(p)
                run.clear()

        for c in children:
            if isinstance(c, Node) and c.tag in BLOCK:
                flush()
                out.extend(self.block(c))
            else:
                run.append(c)
        flush()
        return out

    def block(self, node):
        tag = node.tag
        cls = node.attrs.get("class", "") or ""
        if tag == "div" and "note" in cls.split():
            label, rest = "Note", []
            for c in node.children:
                if isinstance(c, Node) and "note-title" in (c.attrs.get("class") or ""):
                    label = self.para([c]) or label
                else:
                    rest.append(c)
            body = self.blocks(rest)
            if body:
                body[0] = f"**{label}:** {body[0]}"
            else:
                body = [f"**{label}**"]
            return ["\n".join("> " + l if l else ">" for l in "\n\n".join(body).split("\n"))]
        if tag in ("ul", "ol"):
            items, i = [], 0
            for c in node.children:
                if isinstance(c, Node) and c.tag == "li":
                    i += 1
                    marker = f"{i}. " if tag == "ol" else "- "
                    items.append(self.item(marker, self.blocks(c.children)))
            return ["\n".join(items)] if items else []
        if tag == "dl":
            items = []
            for c in node.children:
                if not isinstance(c, Node):
                    continue
                if c.tag == "dt":
                    items.append(self.item("- ", [f"**{self.para(c.children)}**"]))
                elif c.tag == "dd":
                    body = self.blocks(c.children)
                    if items and body:
                        items[-1] += "\n\n" + indent("\n\n".join(body), 2)
                    elif body:
                        items.append(self.item("- ", body))
            return ["\n\n".join(items)] if items else []
        if tag == "pre":
            return ["```\n" + "".join(text_of(node)).strip("\n") + "\n```"]
        return self.blocks(node.children)

    def item(self, marker, blocks):
        if not blocks:
            return marker.rstrip()
        first = indent(blocks[0], len(marker))[len(marker):]
        rest = [indent(b, len(marker)) for b in blocks[1:]]
        return marker + first + "".join("\n\n" + r for r in rest)

    def markdown(self, html_text):
        return "\n\n".join(self.blocks(parse_html(html_text).children))

    def inline_html(self, html_text):
        return self.para(parse_html(html_text).children)


def indent(text, n):
    pad = " " * n
    return "\n".join(pad + l if l else l for l in text.split("\n"))


def text_of(node):
    if isinstance(node, str):
        yield node
    else:
        for c in node.children:
            yield from text_of(c)


def plain(html_text):
    return collapse("".join(text_of(parse_html(html_text)))).strip()


# ------------------------------------------------------------------ source


def read_source(source):
    if re.match(r"^https?://", source):
        req = urllib.request.Request(source, headers={"User-Agent": "ep-skills-wcag/1"})
        try:
            with urllib.request.urlopen(req, timeout=60) as r:
                return r.read()
        except Exception as e:  # noqa: BLE001 - report any fetch failure
            raise SourceError(f"cannot fetch {source}: {e}")
    try:
        return Path(source).read_bytes()
    except OSError as e:
        raise SourceError(f"cannot read {source}: {e}")


def load_source(raw, source):
    try:
        data = json.loads(raw)
    except ValueError as e:
        raise SourceError(f"{source} is not valid JSON: {e}")
    if not isinstance(data, dict) or not isinstance(data.get("principles"), list) or not data["principles"]:
        raise SourceError(f"{source}: missing or empty 'principles'")
    seen = set()
    for pi, p in enumerate(data["principles"]):
        where = f"principles[{pi}]"
        for k in ("num", "handle"):
            if k not in p:
                raise SourceError(f"{source}: {where} missing '{k}'")
        if not isinstance(p.get("guidelines"), list):
            raise SourceError(f"{source}: {where} ({p['num']}) missing 'guidelines'")
        for gi, g in enumerate(p["guidelines"]):
            gwhere = f"{where}.guidelines[{gi}]"
            for k in ("num", "handle"):
                if k not in g:
                    raise SourceError(f"{source}: {gwhere} missing '{k}'")
            if not isinstance(g.get("successcriteria"), list):
                raise SourceError(f"{source}: {gwhere} ({g['num']}) missing 'successcriteria'")
            for si, s in enumerate(g["successcriteria"]):
                swhere = f"{gwhere}.successcriteria[{si}]"
                for k in ("id", "num", "handle", "level", "content"):
                    if k not in s:
                        raise SourceError(f"{source}: {swhere} missing '{k}'")
                if not isinstance(s["num"], str) or not re.fullmatch(r"\d+\.\d+\.\d+", s["num"]):
                    raise SourceError(f"{source}: {swhere} has bad num {s['num']!r}")
                if s["level"] not in LEVELS:
                    raise SourceError(f"{source}: {swhere} ({s['num']}) has unknown level {s['level']!r}")
                if not isinstance(s["id"], str) or not re.fullmatch(r"[a-z0-9-]+", s["id"]):
                    raise SourceError(f"{source}: {swhere} ({s['num']}) has bad id {s['id']!r}")
                for k in ("handle", "content"):
                    if not isinstance(s[k], str):
                        raise SourceError(f"{source}: {swhere} ({s['num']}) '{k}' is not a string")
                if not all(isinstance(v, str) for v in s.get("versions") or []):
                    raise SourceError(f"{source}: {swhere} ({s['num']}) 'versions' must be strings")
                if s["num"] in seen:
                    raise SourceError(f"{source}: duplicate criterion {s['num']}")
                seen.add(s["num"])
    if not seen:
        raise SourceError(f"{source}: no success criteria found")
    return data


# --------------------------------------------------------------- rendering


def sc_filename(s):
    return f"sc/{s['num']}-{s['id']}.md"


def header(source):
    return (f"<!-- GENERATED by {GENERATOR} from {source}. "
            f"Do not edit; run {GENERATOR} update. -->")


def render_techniques(items, conv, depth=0):
    lines = []
    pad = "  " * depth
    for t in items or []:
        if not isinstance(t, dict):
            continue
        parts = []
        if t.get("prefix"):
            parts.append(conv.inline_html(t["prefix"]))
        title = conv.inline_html(t.get("title", ""))
        if t.get("id"):
            parts.append(f"{t['id']}: {title}")
        elif title:
            parts.append(title)
        if t.get("suffix"):
            parts.append(conv.inline_html(t["suffix"]))
        if t.get("note"):
            parts.append(f"({conv.inline_html(t['note'])})")
        line = " ".join(p for p in parts if p)
        children = []
        if t.get("and"):
            if line:
                children.append(f"{pad}  - All of:")
                children += render_techniques(t["and"], conv, depth + 2)
            else:
                line = "All of:"
                children += render_techniques(t["and"], conv, depth + 1)
        children += render_techniques(t.get("techniques"), conv, depth + 1)
        for grp in t.get("groups") or []:
            children.append(f"{pad}  - {conv.inline_html(grp.get('title', ''))}")
            children += render_techniques(grp.get("techniques"), conv, depth + 2)
        if t.get("using"):
            if t.get("and") and line == "All of:":
                # (all of the `and` items) implemented with one of the `using` items
                children.append(f"{pad}  - Using one of:")
                children += render_techniques(t["using"], conv, depth + 2)
            else:
                if not t.get("suffix") and line:
                    line += " using one of:"
                children += render_techniques(t["using"], conv, depth + 1)
        if line:
            lines.append(f"{pad}- {line}")
        lines += children
    return lines


def render_sc(s, p, g, ver, source):
    conv = Converter(TR_URL.format(ver=ver))
    obsolete = s["level"] == ""
    level = s["level"] or "none"
    content = conv.markdown(s["content"])
    content_plain = collapse(plain(s["content"]))
    extra = []
    for d in s.get("details") or []:
        texts = [d.get("text", "")] + [i.get("text", "") for i in d.get("items") or []]
        missing = [t for t in texts if t and plain(t) not in content_plain]
        if not missing:
            continue
        if d.get("type") == "ulist":
            for i in d.get("items") or []:
                h = f"**{conv.inline_html(i['handle'])}:** " if i.get("handle") else ""
                extra.append(f"- {h}{conv.inline_html(i.get('text', ''))}")
        elif d.get("type") == "note":
            extra.append(f"> **{d.get('handle', 'Note')}:** {conv.inline_html(d.get('text', ''))}")
        else:
            extra.append(conv.inline_html(d.get("text", "")))
    out = [
        header(source),
        "",
        f"# {s['num']} {s['handle']} (Level {level})",
        "",
        f"- Principle: {p['num']} {p['handle']}",
        f"- Guideline: {g['num']} {g['handle']}",
        f"- Level: {level}",
        f"- Versions: {', '.join(s.get('versions') or [])}",
    ]
    if obsolete:
        out.append(f"- Status: **Obsolete** in WCAG {dotted(ver)}; do not cite as a finding")
    out += [
        f"- Understanding: {UNDERSTANDING_URL.format(ver=ver, id=s['id'])}",
        f"- Specification: {TR_URL.format(ver=ver)}#{s['id']}",
        "",
        "## Normative text",
        "",
        content,
    ]
    if extra:
        out += ["", "\n\n".join(extra)]
    tech = s.get("techniques") or {}
    if tech.get("sufficient") or tech.get("sufficientNote"):
        out += ["", "## Sufficient techniques", ""]
        if tech.get("sufficientNote"):
            out += [conv.markdown(tech["sufficientNote"]), ""]
        out += render_techniques(tech.get("sufficient"), conv)
    if tech.get("failure"):
        out += ["", "## Failures", ""]
        out += render_techniques(tech["failure"], conv)
    return "\n".join(l.rstrip() for l in "\n".join(out).split("\n")).strip("\n") + "\n"


def cell(s):
    return str(s).replace("|", "\\|")


def render_index(data, ver, source):
    counts = count_levels(data)
    out = [
        header(source),
        "",
        f"# WCAG {dotted(ver)} success criteria",
        "",
        f"Generated from {source}. Each row links to a file with the normative text, "
        "the Understanding link, and sufficient techniques and failures.",
        "",
        f"Counts: A {counts['A']}, AA {counts['AA']}, AAA {counts['AAA']}, "
        f"obsolete {counts['obsolete']}.",
    ]
    for p in data["principles"]:
        out += ["", f"## {p['num']} {p['handle']}"]
        for g in p["guidelines"]:
            out += ["", f"### {g['num']} {g['handle']}", "",
                    "| SC | Name | Level | Versions | Obsolete | File |",
                    "|---|---|---|---|---|---|"]
            for s in g["successcriteria"]:
                f = sc_filename(s)
                out.append(
                    f"| {s['num']} | {cell(s['handle'])} | {s['level'] or '-'} | "
                    f"{', '.join(s.get('versions') or [])} | "
                    f"{'yes' if s['level'] == '' else ''} | [{f}]({f}) |")
    out += [
        "",
        "## License",
        "",
        f"This material is copied from or derived from Web Content Accessibility Guidelines "
        f"(WCAG) {dotted(ver)}, {TR_URL.format(ver=ver)}. "
        f"Copyright © World Wide Web Consortium. "
        f"W3C liability, trademark, and document use rules apply: {LICENSE_URL}",
    ]
    return "\n".join(l.rstrip() for l in out) + "\n"


def count_levels(data):
    c = {"A": 0, "AA": 0, "AAA": 0, "obsolete": 0}
    for s in iter_sc(data):
        c[s["level"] if s["level"] else "obsolete"] = c.get(s["level"] or "obsolete", 0) + 1
    return c


def iter_sc(data):
    for p in data["principles"]:
        for g in p["guidelines"]:
            for s in g["successcriteria"]:
                yield s


def sha256(b):
    return hashlib.sha256(b).hexdigest()


def generate(data, raw, ver, source, dest):
    """Write the full tree into dest (an empty directory)."""
    (dest / "sc").mkdir(parents=True)
    files = {}

    def write(rel, text):
        b = text.encode("utf-8")
        (dest / rel).write_bytes(b)
        files[rel] = sha256(b)

    for p in data["principles"]:
        for g in p["guidelines"]:
            for s in g["successcriteria"]:
                write(sc_filename(s), render_sc(s, p, g, ver, source))
    write("index.md", render_index(data, ver, source))
    manifest = {
        "generator": GENERATOR,
        "source": source,
        "wcag_version": dotted(ver),
        "fetched_at": datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "source_sha256": sha256(raw),
        "counts": count_levels(data),
        "license": f"W3C Document License, {LICENSE_URL}. Copyright © World Wide Web Consortium.",
        "files": dict(sorted(files.items())),
    }
    (dest / "manifest.json").write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n",
                                        encoding="utf-8")


def validate_tree(dest):
    idx = parse_index((dest / "index.md").read_text(encoding="utf-8"))
    if not idx:
        raise SourceError("generated index has no criteria")
    for num, row in idx.items():
        if not (dest / row["file"]).is_file():
            raise SourceError(f"generated index row {num} has no file {row['file']}")


def sc_by_num(tree):
    out = {}
    sc = tree / "sc"
    if sc.is_dir():
        for f in sorted(sc.glob("*.md")):
            m = re.match(r"(\d+\.\d+\.\d+)-", f.name)
            if m:
                out[m.group(1)] = f.read_bytes()
    return out


def diff_trees(old, new):
    a, b = sc_by_num(old), sc_by_num(new)

    def body(x):  # ignore the header line, which names the source
        return x.split(b"\n", 1)[1] if b"\n" in x else x

    added = sorted(set(b) - set(a), key=numkey)
    removed = sorted(set(a) - set(b), key=numkey)
    changed = sorted((n for n in set(a) & set(b) if body(a[n]) != body(b[n])), key=numkey)
    return added, removed, changed


def numkey(n):
    return tuple(int(x) for x in n.split("."))


def print_diff(added, removed, changed, index):
    def name(n):
        r = index.get(n)
        return f"{n} {r['handle']} ({r['level'] or 'obsolete'})" if r else n
    print(f"added: {len(added)}, removed: {len(removed)}, changed: {len(changed)}")
    for label, nums in (("added", added), ("removed", removed), ("changed", changed)):
        for n in nums:
            print(f"  {label}: {name(n)}")


def source_label(source):
    """What generated files record as their source: the URL, or only a local file's name."""
    if re.match(r"^https?://", source):
        return source
    return f"local file {Path(source).name}"


def cmd_update(args):
    ver = args.version
    fetch = args.source or SOURCE_URL.format(ver=ver)
    source = source_label(fetch)
    out = Path(args.out).resolve()
    try:
        raw = read_source(fetch)
        data = load_source(raw, source)
        # render once up front so odd field types fail here, before anything is written
        with tempfile.TemporaryDirectory() as td:
            (Path(td) / "wcag").mkdir()
            generate(data, raw, ver, source, Path(td) / "wcag")
    except (KeyError, TypeError, AttributeError, ValueError) as e:
        print(f"error: {source}: unexpected content ({type(e).__name__}: {e})", file=sys.stderr)
        print(f"error: {rel(out)} left unchanged", file=sys.stderr)
        return 2
    except SourceError as e:
        print(f"error: {e}", file=sys.stderr)
        print(f"error: {rel(out)} left unchanged", file=sys.stderr)
        return 2

    if args.dry_run:
        mf = out / "manifest.json"
        if mf.is_file():
            try:
                old = json.loads(mf.read_text(encoding="utf-8"))
            except ValueError:
                old = {}
            if old.get("source_sha256") == sha256(raw) and old.get("wcag_version") == dotted(ver):
                print(f"up to date: {source} matches {rel(mf)}")
                return 0
        with tempfile.TemporaryDirectory() as td:
            tmp = Path(td) / "wcag"
            tmp.mkdir()
            generate(data, raw, ver, source, tmp)
            idx = parse_index((tmp / "index.md").read_text(encoding="utf-8"))
            old_idx = parse_index((out / "index.md").read_text(encoding="utf-8")) if (out / "index.md").is_file() else {}
            added, removed, changed = diff_trees(out, tmp)
            print(f"dry run: {source} (WCAG {dotted(ver)}) vs {rel(out)}; nothing written")
            print_diff(added, removed, changed, {**old_idx, **idx})
        return 0

    out.parent.mkdir(parents=True, exist_ok=True)
    tmp = Path(tempfile.mkdtemp(prefix=".wcag-new-", dir=out.parent))
    old_tmp = None
    try:
        new = tmp / "wcag"
        new.mkdir()
        generate(data, raw, ver, source, new)
        validate_tree(new)
        idx = parse_index((new / "index.md").read_text(encoding="utf-8"))
        old_idx = parse_index((out / "index.md").read_text(encoding="utf-8")) if (out / "index.md").is_file() else {}
        added, removed, changed = diff_trees(out, new)
        if out.exists():
            moved = tmp / "old"
            os.rename(out, moved)
            old_tmp = moved
        try:
            os.rename(new, out)
        except OSError:
            if old_tmp:
                os.rename(old_tmp, out)
                old_tmp = None
            raise
    except (SourceError, OSError) as e:
        print(f"error: {e}", file=sys.stderr)
        if out.exists():
            print(f"error: {rel(out)} left unchanged", file=sys.stderr)
        return 2
    finally:
        if old_tmp and old_tmp.exists() and not out.exists():
            print(f"error: could not restore {rel(out)}; the previous tree is in {rel(old_tmp)}",
                  file=sys.stderr)
        else:
            shutil.rmtree(tmp, ignore_errors=True)
    c = count_levels(data)
    print(f"wrote {rel(out)} from {source} (WCAG {dotted(ver)}): "
          f"{len(idx)} criteria (A {c['A']}, AA {c['AA']}, AAA {c['AAA']}, obsolete {c['obsolete']})")
    print_diff(added, removed, changed, {**old_idx, **idx})
    if changed or removed:
        print("review the matching sections of references/checks.md and audit.md, then run "
              f"{GENERATOR} check")
    return 0


# ------------------------------------------------------------------- check

ROW = re.compile(r"^\| (\d+\.\d+\.\d+) \| (.*?) \| (A|AA|AAA|-) \| (.*?) \| (yes|) \| \[([^\]]+)\]")


def parse_index(text):
    rows = {}
    for line in text.splitlines():
        m = ROW.match(line)
        if m:
            rows[m.group(1)] = {
                "handle": m.group(2).replace("\\|", "|"),
                "level": "" if m.group(3) == "-" else m.group(3),
                "obsolete": m.group(5) == "yes",
                "file": m.group(6),
            }
    return rows


HEADING = re.compile(r"^## (\d+\.\d+\.\d+)\b\s*(.*?)\s*$")
# any criterion-shaped number, bare or after "SC"; a following capitalised name is checked too
CITE = re.compile(r"(?<![\d.])(\d+\.\d+\.\d+)(?![\d.]*\d)(?: ([A-Z][^|\n]*))?")


def check_guidance(path, index):
    problems = []
    section = "(top of file)"
    for no, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if line.startswith("#"):
            section = line.lstrip("#").strip()
        m = HEADING.match(line)
        cites = [(m.group(1), m.group(2), True)] if m else []
        rest = line[m.end(1):] if m else line
        cites += [(n, name, False) for n, name in CITE.findall(rest)]
        for num, name, is_heading in cites:
            where = f"{path.name}:{no} (section '{section}')"
            row = index.get(num)
            if row is None:
                problems.append(f"{where} cites {num}, which is not in the index")
            elif row["obsolete"]:
                problems.append(f"{where} cites {num}, which is obsolete")
            elif is_heading and name and name != row["handle"]:
                problems.append(f"{where} heading name '{name}' does not match the index "
                                f"name '{row['handle']}' for {num}")
            elif not is_heading and name and not name.startswith(row["handle"]):
                problems.append(f"{where} name after {num} does not match the index "
                                f"name '{row['handle']}'")
    return problems


def cmd_check(args):
    out = Path(args.out).resolve()
    problems = []
    mf = out / "manifest.json"
    try:
        manifest = json.loads(mf.read_text(encoding="utf-8"))
        files = manifest["files"]
    except (OSError, ValueError, KeyError) as e:
        print(f"error: cannot read {rel(mf)}: {e}; run {GENERATOR} update", file=sys.stderr)
        return 1

    for path, digest in sorted(files.items()):
        f = out / path
        if not f.is_file():
            problems.append(f"missing generated file: {rel(f)}")
        elif sha256(f.read_bytes().replace(b"\r\n", b"\n")) != digest:
            problems.append(f"edited by hand: {rel(f)} differs from manifest.json; "
                            f"do not edit generated files, run {GENERATOR} update instead")
    for f in sorted(out.rglob("*")):
        r = f.relative_to(out).as_posix()
        if f.is_file() and r != "manifest.json" and r not in files:
            problems.append(f"not generated (absent from manifest.json): {rel(f)}")

    index = {}
    if (out / "index.md").is_file():
        index = parse_index((out / "index.md").read_text(encoding="utf-8"))
        if not index:
            problems.append(f"{rel(out / 'index.md')} has no criteria rows")
        listed = {}
        for num, row in index.items():
            listed[row["file"]] = num
            f = out / row["file"]
            if not f.is_file():
                problems.append(f"index row {num} points to missing file {rel(f)}")
                continue
            lines = f.read_text(encoding="utf-8").splitlines()
            if len(lines) < 3 or not lines[2].startswith(f"# {num} "):
                problems.append(f"{rel(f)} heading does not match index row {num}")
        for f in sorted((out / "sc").glob("*.md")) if (out / "sc").is_dir() else []:
            r = f.relative_to(out).as_posix()
            if r not in listed:
                problems.append(f"orphan criterion file not in index: {rel(f)}")

    for name in GUIDANCE_FILES:
        g = out.parent / name
        if g.is_file():
            problems += check_guidance(g, index)

    if problems:
        for p in problems:
            print(f"FAIL {p}")
        print(f"{len(problems)} problem(s) in {rel(out)}", file=sys.stderr)
        return 1
    cited = [n for n in GUIDANCE_FILES if (out.parent / n).is_file()]
    print(f"ok: {rel(out)} matches manifest ({manifest.get('wcag_version')}, "
          f"{len(index)} criteria); guidance checked: {', '.join(cited) or 'none'}")
    return 0


def rel(p):
    try:
        return Path(p).resolve().relative_to(Path.cwd()).as_posix()
    except ValueError:
        return str(p)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    sub = ap.add_subparsers(dest="mode", required=True)
    up = sub.add_parser("update", help="fetch wcag.json and regenerate the references")
    up.add_argument("--source", help="URL or file to read instead of the W3C URL")
    up.add_argument("--version", default=VERSION, help=f"WCAG version digits (default {VERSION})")
    up.add_argument("--dry-run", action="store_true", help="report changes; write nothing")
    up.add_argument("--out", default=str(DEFAULT_OUT), help=argparse.SUPPRESS)
    ck = sub.add_parser("check", help="offline drift check")
    ck.add_argument("--out", default=str(DEFAULT_OUT), help=argparse.SUPPRESS)
    args = ap.parse_args(argv)
    return cmd_update(args) if args.mode == "update" else cmd_check(args)


if __name__ == "__main__":
    sys.exit(main())
