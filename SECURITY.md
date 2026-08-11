# Security policy

## Scope

This project is a local, validation-first authoring workflow. It is not a hosted service and does not require credentials for its static checks.

## Reporting a vulnerability

Do not open a public issue containing credentials, private files, personal data, or an exploit that could affect another user's system. Use the repository's private security-reporting channel when one is configured; otherwise contact the maintainers through the private channel associated with the repository before disclosure.

Include the affected file, a minimal reproduction using synthetic data, impact, and a suggested fix. Redact secrets from logs and reproductions.

## Local execution boundary

Some delivery commands can inspect project files and may optionally execute a project-supplied builder. Static checks are the default. Treat `--execute-builder` as arbitrary local code execution: use it only in a trusted, isolated workspace and never expose credentials to the child process.

The repository does not promise sandboxing, network isolation, or SillyTavern runtime safety. Review scripts before running them on untrusted projects.

## Secret hygiene

- Keep `.env*`, tokens, private keys, logs, card exports, and local reports out of Git.
- Use synthetic fixtures in tests.
- Run the public-release audit before publishing.
- If a credential was committed, revoke it immediately; deleting the current file is not enough because Git history may retain it.
