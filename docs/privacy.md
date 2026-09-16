# Privacy review

Backlog Skills is designed to be shared. Its examples use fictional task IDs and
general project paths, and its helpers use only Python's standard library.

Run this release check from the repository root:

```bash
python3 scripts/privacy_audit.py
```

It scans text files for email addresses, user-home paths, private-key blocks,
and likely access tokens. The scan is intentionally conservative. Review any
new prose, screenshots, archives, and generated assets as well: automated
checks cannot decide whether surrounding context is safe to publish.

For GitHub releases, use a repository-local Git identity with a GitHub no-reply
address or another identity you are comfortable publishing. Check the rendered
repository and release assets before announcing a release.
