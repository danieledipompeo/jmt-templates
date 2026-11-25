# JMT community templates

Templates for JSIMgraph (part of [JMT](http://jmt.sourceforge.net)) in the `.jsimgt` format: a data-only
description of a model that JMT turns into a canvas after asking for a few parameters.

* **Use them:** in JSIMgraph open *Templates → Community...*, pick a template and install it.
* **Share one:** in JSIMgraph choose *Templates → Share...*; JMT logs you in to GitHub and opens a pull request here.
  You can also open a pull request by hand that adds `templates/<name>.jsimgt`.

## Rules for a submission
* One file, `templates/<slug>.jsimgt` (lower-case letters, digits and `-`, at most 64 characters).
* The `<meta>` element has a unique name, an author, a version and a short description.
* At most 1 MiB, valid against `schema/jsimgt.xsd`, no markup in texts. CI checks all of this.
* To update a template raise its `version`.
* Every pull request is reviewed by a maintainer before it is merged; the index is then published automatically.

See `docs/jsimgt-format.md` in the JMT repository for the format.
