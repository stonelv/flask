<!--
Before opening a PR, open a ticket describing the issue or feature the
PR will address. An issue is not required for fixing typos in
documentation, or other simple non-code changes.

Replace this comment with a description of the change. Describe how it
addresses the linked ticket.
-->

<!--
Link to relevant issues or previous PRs, one per line. Use "fixes" to
automatically close an issue.

fixes #<issue number>
-->

## Checklist

- [ ] Add tests that demonstrate the correct behavior of the change.
- [ ] Add or update relevant docs, in the ``docs`` folder and in code.
- [ ] Add a changelog fragment in ``changelog.d/`` (see below).
- [ ] Add ``.. versionchanged::`` entries in any relevant code docs.
- [ ] Linting passes (``make lint`` or ``tox run -e style``).
- [ ] Type checking passes (``make type`` or ``tox run -e typing``).

<!--
Changelog fragment: create a file in changelog.d/ named
<issue-or-pr-number>.<type>.rst where <type> is one of:
breaking, feature, fix, docs, internal

Example: changelog.d/1234.feature.rst with content:
    Added support for new widget. :pr:`1234`
-->

