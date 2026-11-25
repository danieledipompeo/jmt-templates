#!/usr/bin/env python3
"""Validates submitted .jsimgt templates. Usage: validate.py [--changed LISTFILE] FILE..."""
import os
import re
import sys
import xml.etree.ElementTree as ET

SLUG = re.compile(r"^[a-z0-9][a-z0-9-]{0,63}\.jsimgt$")
MAX_BYTES = 1024 * 1024
# the rules below mirror JMT's ModelGuard for the model embedded in version-2 templates
CLASS_PATH = re.compile(r"java\.lang\.(Integer|Double|Boolean|String|Object|Long)|java\.util\.HashMap"
                        r"|(jmt\.engine\.)?(NetStrategies|NodeSections|random|QueueNet)(\.[A-Za-z0-9_]+)+")
LOG_ATTRIBUTES = ("logPath", "logDelimiter", "logDecimalSeparator", "logReplaceMode")


def check_log_name(parameter, parents):
    """A Logger may only write global.csv or a file named after its station."""
    section = parents.get(parameter)
    node = parents.get(section)
    if section is None or node is None or section.get("className") != "LogTunnel":
        return ["a log file name outside a Logger"]
    station = node.get("name", "")
    for v in parameter.iter("value"):
        f = v.text or ""
        if len(v) or f not in ("global.csv", station + ".csv") or f.startswith(".") or any(c in f for c in "/\\:"):
            return ["the Logger '%s' may only write global.csv or a file named after itself" % station]
    return []


def check_model(root):
    """Problems of the model embedded in a version-2 template."""
    model = root.find("model")
    if model is None or len(model) != 1 or model[0].tag != "archive":
        return ["<model> must contain exactly one archive"]
    archive = model[0]
    out = []
    tags = [c.tag for c in archive]
    if any(t not in ("sim", "jmodel", "results") for t in tags):
        out.append("unexpected section in the model")
    if tags.count("sim") != 1 or tags.count("jmodel") > 1:
        out.append("the file must contain exactly one model")
    parents = {c: p for p in archive.iter() for c in p}
    for el in archive.iter():
        if el.tag in ("results", "parametric"):
            out.append("%s are not allowed in a template" % el.tag)
        if el.tag == "sim":
            out += ["the model sets the log option %s" % a for a in LOG_ATTRIBUTES if el.get(a)]
        class_path = el.get("classPath")
        if class_path is not None:
            if "Replayer" in class_path or "Trace" in class_path:
                out.append("trace files cannot be part of a template")
            elif not CLASS_PATH.fullmatch(class_path):
                out.append("unexpected class '%s'" % class_path)
        if el.get("className") is not None and not re.fullmatch("[A-Za-z]+", el.get("className")):
            out.append("unexpected class '%s'" % el.get("className"))
        if el.get("verbose", "").lower() == "true":
            out.append("a performance index has logging switched on")
        if el.tag in ("parameter", "subParameter"):
            key = el.get("name", "")
            if key == "logfileName":
                out += check_log_name(el, parents)
            elif "file" in key.lower() or "path" in key.lower():
                if any("".join(v.itertext()).strip() for v in el.iter("value")):
                    out.append("the model names a file or folder (%s)" % key)
    return out


def check_changed(names):
    """Every changed path must be a template file directly under templates/."""
    out = []
    for n in names:
        n = n.strip()
        if n and not (n.startswith("templates/") and n.count("/") == 1 and n.endswith(".jsimgt")):
            out.append("%s: submissions may only add or change files directly under templates/" % n)
    return out


def check_file(path):
    problems, name = [], os.path.basename(path)
    if not SLUG.match(name):
        problems.append("%s: file name must be lower-case letters, digits and '-' plus .jsimgt (max 64 characters)" % name)
    if os.path.getsize(path) > MAX_BYTES:
        problems.append("%s: larger than %d bytes" % (name, MAX_BYTES))
        return problems, None
    data = open(path, "rb").read()
    if b"<!DOCTYPE" in data or b"<!ENTITY" in data:
        problems.append("%s: DOCTYPE/entity declarations are not allowed" % name)
        return problems, None
    try:
        root = ET.fromstring(data)
    except ET.ParseError as e:
        problems.append("%s: not well-formed XML (%s)" % (name, e))
        return problems, None
    meta = root.find("meta")
    if root.tag != "jsimgt" or meta is None:
        problems.append("%s: root must be <jsimgt> with a <meta> element" % name)
        return problems, None
    for k in ("name", "author", "version"):
        if not meta.get(k, "").strip():
            problems.append("%s: <meta> needs a non-empty %s" % (name, k))
    version = root.get("version")
    if version == "2":
        problems += ["%s: %s" % (name, m) for m in check_model(root)]
    elif version != "1":
        problems.append("%s: unknown version '%s'" % (name, version))
    for el in root.iter():
        values = list(el.attrib.values()) + [el.text or "", el.tail or ""]
        if any("<" in v for v in values):
            problems.append("%s: markup ('<') in text of <%s> is not allowed" % (name, el.tag))
            break
    return problems, meta.get("name", "").strip()


def check(paths, changed=None):
    problems, names = [], {}
    if changed is not None:
        problems += check_changed(changed)
    for p in paths:
        pr, nm = check_file(p)
        problems += pr
        if nm:
            if nm.lower() in names:
                problems.append("%s: duplicate name '%s' (also used by %s)" % (os.path.basename(p), nm, names[nm.lower()]))
            names[nm.lower()] = os.path.basename(p)
    return problems


def main(argv):
    changed, paths = None, []
    i = 0
    while i < len(argv):
        if argv[i] == "--changed":
            changed = open(argv[i + 1]).read().splitlines()
            i += 2
        else:
            paths.append(argv[i])
            i += 1
    # uniqueness is checked against every published template as well as the submitted ones
    for d in {os.path.dirname(p) or "." for p in paths}:
        for f in sorted(os.listdir(d)):
            full = os.path.join(d, f)
            if f.endswith(".jsimgt") and full not in paths:
                paths.append(full)
    problems = check(paths, changed)
    for m in problems:
        print(m)
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
