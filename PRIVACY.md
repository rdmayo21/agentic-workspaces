# Agentic Workspaces privacy policy

Publisher: Daniel Mayo. Effective September 30, 2026.

Agentic Workspaces is a collection of instructions, templates, and local
Python scripts. It has no publisher-operated server, analytics, telemetry,
advertising, or account system. The publisher does not receive your
workspace files or conversation content through the plugin.

The plugin uses project information you choose to save: descriptions,
decisions, next actions, research, reference files, and captured notes. It
stores these in `~/ai-workspaces/` in the execution environment where you
run it, to help you resume projects across sessions. Setup also creates
pointer skills or links in your installed agents' configuration directories.
Git commits may contain your configured Git author name and email address.
Local files and Git history remain until you remove them; archiving a
workspace preserves its files. Uninstalling the plugin does not remove your
workspace store.

No workspace data is sent to the publisher. If you authorize Git backup,
your files and commit metadata are sent to the private remote you choose
and retained under that service's policies. You control the remote,
sharing, backup copies, and retention. The secret-pattern check in the
sync script is a limited tripwire, not a guarantee that every sensitive
item will be detected. Do not store passwords, API keys, government
identifiers, payment-card information, or protected health information.

Your AI host processes the content the assistant reads under its own
privacy and retention policies. Running in a hosted execution environment
stores files there rather than on your personal computer; persistent
storage or an authorized private backup is needed to keep them. The plugin
does not change your host's data policies or grant it additional permissions.

You can inspect or edit every saved file, omit information you do not want
saved, disable backups, archive workspaces, or remove your local store and
backup copies. Deleting a working file does not remove prior Git history
or remote and local backups.

For support or privacy questions, use
[GitHub Issues](https://github.com/rdmayo21/agentic-workspaces/issues).
Issues are public: do not include private workspace content or credentials.
