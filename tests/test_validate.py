import hashlib
import os
import sys
import tempfile
import unittest
import xml.etree.ElementTree as ET

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))
import build_index
import validate

ROOT = os.path.join(os.path.dirname(__file__), "..")
GOOD = open(os.path.join(ROOT, "templates", "parallel.jsimgt"), encoding="utf-8").read()


V2 = open(os.path.join(ROOT, "tests", "fixtures", "queue-v2.jsimgt"), encoding="utf-8").read()


def write(d, name, text):
    p = os.path.join(d, name)
    with open(p, "w", encoding="utf-8") as f:
        f.write(text)
    return p


class ValidateTest(unittest.TestCase):
    def setUp(self):
        self.d = tempfile.mkdtemp()

    def problems(self, *paths, **kw):
        return validate.check(list(paths), **kw)

    def test_good_passes(self):
        self.assertEqual([], self.problems(write(self.d, "good-one.jsimgt", GOOD)))

    def test_real_templates_pass(self):
        t = os.path.join(ROOT, "templates")
        paths = [os.path.join(t, n) for n in sorted(os.listdir(t))]
        self.assertEqual([], self.problems(*paths))

    def test_bad_slug(self):
        out = self.problems(write(self.d, "Bad_Name.jsimgt", GOOD))
        self.assertTrue(any("file name" in m for m in out), out)

    def test_markup_in_text(self):
        bad = GOOD.replace('name="Parallel"', 'name="&lt;b&gt;x"', 1)
        out = self.problems(write(self.d, "x.jsimgt", bad))
        self.assertTrue(any("markup" in m for m in out), out)

    def test_oversize(self):
        out = self.problems(write(self.d, "big.jsimgt", GOOD + " " * (1024 * 1024 + 1)))
        self.assertTrue(any("larger than" in m for m in out), out)

    def test_duplicate_name(self):
        a = write(self.d, "a.jsimgt", GOOD)
        b = write(self.d, "b.jsimgt", GOOD)
        out = self.problems(a, b)
        self.assertTrue(any("duplicate name" in m for m in out), out)

    def test_missing_meta_and_doctype(self):
        out = self.problems(write(self.d, "m.jsimgt", '<jsimgt version="1"><meta name="x"/></jsimgt>'))
        self.assertTrue(any("author" in m for m in out), out)
        out = self.problems(write(self.d, "e.jsimgt", '<!DOCTYPE a [<!ENTITY x "y">]><jsimgt/>'))
        self.assertTrue(any("DOCTYPE" in m for m in out), out)

    def test_changed_files_only_templates(self):
        self.assertEqual([], validate.check_changed(["templates/a.jsimgt"]))
        self.assertTrue(validate.check_changed([".github/workflows/x.yml"]))
        self.assertTrue(validate.check_changed(["templates/sub/a.jsimgt"]))


class IndexTest(unittest.TestCase):
    def test_index_matches_files(self):
        out = tempfile.mkdtemp()
        t = os.path.join(ROOT, "templates")
        build_index.build(t, out)
        root = ET.parse(os.path.join(out, "index.xml")).getroot()
        entries = root.findall("template")
        self.assertEqual(4, len(entries))
        for e in entries:
            f = e.get("file")
            self.assertTrue(f.endswith(".jsimgt"))
            data = open(os.path.join(t, f), "rb").read()
            self.assertEqual(hashlib.sha256(data).hexdigest(), e.get("sha256"))
            self.assertTrue(os.path.isfile(os.path.join(out, "templates", f)))
            self.assertTrue(e.get("name") and e.get("version"))


class ValidateV2Test(unittest.TestCase):
    def setUp(self):
        self.d = tempfile.mkdtemp()

    def check(self, text):
        return validate.check([write(self.d, "x.jsimgt", text)])

    def refused(self, old, new, reason, count=1):
        self.assertIn(old, V2)
        out = self.check(V2.replace(old, new, count))
        self.assertTrue(any(reason in m for m in out), (reason, out))

    def test_saved_template_passes(self):
        self.assertEqual([], self.check(V2))

    def test_foreign_classes(self):
        self.refused('classPath="random.Exponential"', 'classPath="java.io.FileWriter"', "unexpected class")
        self.refused('className="Server"', 'className="a.b.C"', "unexpected class")
        self.refused('classPath="random.Exponential"', 'classPath="random.Replayer"', "trace")

    def test_sections(self):
        self.refused("</sim>", "</sim><results/>", "results")
        self.refused("</sim>", "</sim><parametric/>", "parametric")
        self.refused("</sim>", "</sim><sim/>", "exactly one model")
        self.refused("</sim>", "</sim><other/>", "unexpected section")
        self.refused("<model>", "<model><x/>", "exactly one archive")

    def test_logging_and_files(self):
        self.refused("<sim ", '<sim logPath="/tmp" ', "log option")
        self.refused('verbose="false"', 'verbose="TRUE"', "logging")
        self.refused('name="logJobID"', 'name="fileName"', "file or folder")
        self.refused("<value/>", "<value>/tmp/</value>", "file or folder")

    def test_logger_file_name(self):
        for bad in ("../x.csv", ".bashrc", "other.csv"):
            self.refused("<value>global.csv</value>", "<value>%s</value>" % bad, "may only write")
        self.refused("<value>global.csv</value>", "<value>global.csv<x/></value>", "may only write")

    def test_fork_entries_and_class_switch_numbers_are_not_files_or_foreign_classes(self):
        entry = ('<subParameter classPath="NetStrategies.ForkStrategies.OutPath" name="OutPathEntry"><value>S</value></subParameter>'
                 '<subParameter classPath="java.lang.Float" name="cell"><value>1.0</value></subParameter>')
        self.assertIn("</section>", V2)
        self.assertEqual([], self.check(V2.replace("</section>", entry + "</section>", 1)))

    def test_markup(self):
        self.refused("<refClass>C</refClass>", "<refClass>&lt;html&gt;</refClass>", "markup")

    def test_unknown_version(self):
        out = self.check(V2.replace('<jsimgt version="2">', '<jsimgt version="3">'))
        self.assertTrue(any("version" in m for m in out), out)


if __name__ == "__main__":
    unittest.main()


class WorkflowTest(unittest.TestCase):
    def test_pr_validation_cannot_be_bypassed(self):
        text = open(os.path.join(ROOT, ".github", "workflows", "validate.yml"), encoding="utf-8").read()
        self.assertNotIn("paths:", text)  # every PR is validated
        self.assertIn("base/scripts/validate.py", text)  # the base branch's checker runs, not the PR's own copy
        self.assertIn("base/schema/jsimgt.xsd", text)
