# Security Policy

## Supported versions

Only the latest release gets security fixes.

## Reporting a vulnerability

Please **don't open a public issue**. Report it privately through
[GitHub Security Advisories](https://github.com/JakobAyo/tutor-agent/security/advisories/new).
You'll get an answer within a week.

`tutor-agent` reads your Claude Code transcripts and passes excerpts to `claude -p`, so the most
relevant issues are: transcript content escaping the sandboxed model call, the hook affecting the
observed session, and local data (`~/.local/share/tutor-agent/`) being readable by other users.
