# Classifying the door for requested work

Every drafted issue gets a door call: **one-way door** or **two-way door**, with a
one-sentence reason. These rules are `ep-open-pr`'s classification, applied to the work
the issue asks for rather than to a diff. Decide from what doing the work would change,
not from the issue's wording alone.

**Two-way door:** the finished work could be fully undone with `git revert` and a
redeploy, leaving no lasting effect on users, data, or other systems. Examples: internal
refactors, bug fixes, new code behind a flag, tests, docs, CI changes that touch only
this repo.

**One-way door:** doing the work would leave some effect after a revert, or reverting it
would itself break someone. Call the issue one-way if the work asks for any of:

- data or schema changes that drop, rewrite, or migrate stored data (destructive
  migrations, backfills, format changes to persisted files or caches)
- removing or changing public interfaces other people depend on: API endpoints, CLI
  flags, config keys, library exports, event or message formats, file formats
- releases or publishing: version bumps that trigger a publish, package, image, or
  artifact pushes, tags
- external side effects: sending email or notifications, calls to third-party APIs that
  create or delete things, billing, infrastructure creation or deletion
- security or access changes: permissions, auth flows, secrets rotation, CORS, data
  exposure (anything leaked cannot be taken back)
- renames or deletions of things others reference by name: database tables or columns,
  queues, buckets, URLs, feature-flag keys

Judgment calls:

- A migration or other destructive step counts as soon as the work would add it, even if
  nothing would run it yet: merging it makes it deployable.
- An interface is public when code outside this repo can reach it: anything exported
  from a published package, a documented CLI flag or endpoint, or (in an unpublished
  repo) anything the README or docs tell users to use. Changes to code only this repo
  calls are internal, even when the issue calls the work a refactor.
- A version bump counts as a release only if the repo's CI or scripts publish on it;
  check the workflows before deciding.
- When the issue leaves the scope unclear, call it a one-way door and put what is
  uncertain in the reason, as an open question.

**In the body:** write the call in bold with its one-sentence reason. For a one-way door,
name each irreversible element on its own line with a mitigation to plan for (backup,
migration rollback script, deprecation period, feature flag, staged rollout). For a
two-way door, the single sentence is enough.

When the door is one-way because a public interface would break, say in the reason that
the eventual PR is a breaking change (`type(scope)!:` in Conventional Commits).
