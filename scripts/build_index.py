#!/usr/bin/env python3
"""Usage: build_index.py TEMPLATES_DIR OUT_DIR  -> OUT_DIR/index.xml and OUT_DIR/templates/*.jsimgt"""
import hashlib
import os
import shutil
import sys
import xml.etree.ElementTree as ET


def build(templates_dir, out_dir):
    os.makedirs(os.path.join(out_dir, "templates"), exist_ok=True)
    root = ET.Element("templates")
    for f in sorted(os.listdir(templates_dir)):
        if not f.endswith(".jsimgt"):
            continue
        src = os.path.join(templates_dir, f)
        data = open(src, "rb").read()
        meta = ET.fromstring(data).find("meta")
        ET.SubElement(root, "template", {
            "file": f,
            "name": meta.get("name", ""),
            "author": meta.get("author", ""),
            "version": meta.get("version", ""),
            "date": meta.get("date", ""),
            "description": meta.get("description", ""),
            "sha256": hashlib.sha256(data).hexdigest(),
        })
        shutil.copy(src, os.path.join(out_dir, "templates", f))
    ET.ElementTree(root).write(os.path.join(out_dir, "index.xml"), encoding="utf-8", xml_declaration=True)


if __name__ == "__main__":
    build(sys.argv[1], sys.argv[2])
