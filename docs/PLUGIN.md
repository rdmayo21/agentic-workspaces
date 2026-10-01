# Agentic Workspaces plugin

This repository is also an installable skills-only OpenAI plugin. It contains
the public workspace manager, templates, and scripts, not the publisher's
personal workspace store. No MCP server or connected account is required.

## Install from GitHub

With a current Codex CLI:

```bash
codex plugin marketplace add rdmayo21/agentic-workspaces
codex plugin add agentic-workspaces@agentic-workspaces
```

Start a new chat and ask: “Set up persistent workspaces for my ongoing
projects.” The bundled `new-ai-workspace` skill guides setup and project
creation. Installing the plugin does not itself create a workspace store.

The installer copies the manager into `~/ai-workspaces/`, initializes local
Git without a remote, and wires pointer skills for installed agents. It
preserves an existing workspace store. Choose and authorize a **private**
remote before enabling off-device backup. The public starter repo is never
your personal backup destination.

Python 3.11+, Git, and persistent filesystem access on macOS or Linux are
required. A temporary cloud computer needs persistent storage or an
authorized private backup for cross-session continuity. Uninstalling the
plugin leaves your workspace data intact. See [privacy policy](../PRIVACY.md).

## Build the upload ZIP

```bash
python3 -m unittest discover -s tests -v
python3 scripts/package_plugin.py
```

The builder writes `dist/agentic-workspaces-<version>.zip` using an explicit
allowlist: the root manifest, icons, license, privacy policy, README, and
workspace skill resources. It excludes Git history, local stores, tests,
site/talk files, and build caches. `plugin.json` is the metadata source;
`skills/new-ai-workspace/` is the implementation source.

## Submit to the public directory

GitHub distribution and OpenAI Directory publication are separate.
[OpenAI's submission portal](https://platform.openai.com/plugins) requires
a verified developer identity. Upload the ZIP, resolve automated metadata
and skill findings, submit for review, then publish the approved version.
Never describe a package as directory-listed until the portal confirms
publication. Skills-only packages do not require MCP review test cases or
a video walkthrough.

Official references, checked September 30, 2026:
[package format](https://developers.openai.com/plugins/build/plugins),
[submission workflow](https://developers.openai.com/plugins/deploy/submission),
[plugin guidelines](https://developers.openai.com/plugins/plugin-guidelines).
