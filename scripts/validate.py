#!/usr/bin/env python3
"""Validates submitted .jsimgt templates. Usage: validate.py [--changed LISTFILE] FILE..."""
import os
import re
import sys
import xml.etree.ElementTree as ET

SLUG = re.compile(r"^[a-z0-9][a-z0-9-]{0,63}\.jsimgt$")
MAX_BYTES = 1024 * 1024


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
    for el in root.iter():
        values = list(el.attrib.values()) + [el.text or ""]
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
