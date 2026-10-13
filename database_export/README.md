# Database backups are not source files

Do not commit JSON database exports, user data, password hashes, test attempts/results, or database archive files to this repository.

Keep encrypted backups in restricted storage outside the working tree. Before a restore, verify the target database and backup provenance and take a fresh backup. Never use a restore command that drops production collections without a separately reviewed migration/restore plan.

Older commits may still contain former exports. See the repository-root `SECURITY.md` for history-cleanup guidance.
