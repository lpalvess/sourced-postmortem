# Security Policy

## Supported versions

The current version is 1.0.0. Only the latest commit on `main` is supported.

## Reporting a vulnerability

Please do not open a public issue for a security problem.

Use GitHub private vulnerability reporting: open the repository's **Security** tab and choose **Report a vulnerability**. Include the affected commit, a minimal input (postmortem, evidence file or TOML) that reproduces the problem, and the impact you expect. Do not include real credentials in the report.

We aim to acknowledge a report within 7 days.

## Scope

In scope:

- Code execution triggered by input files (the postmortem, the evidence files, the TOML config, CLI arguments).
- Any network access at runtime. The tool is designed to work fully offline.
- Writes outside the output folder.
- A credential that escapes redaction and ends up in the generated files (`relatorio.json`, `relatorio.md` or `diagrama.excalidraw`).

## Not supported

- Running the tool outside the provided container script and then reporting problems caused by that environment.
- Issues that need a modified copy of the code, or a modified container setup.
- Older commits and forks.
- Credentials in formats outside the masked patterns, such as `Authorization: Basic ...` or `X-Api-Key` style headers (these are known gaps, not vulnerabilities).
- Wrong or missing findings in a report (open a regular issue instead).
