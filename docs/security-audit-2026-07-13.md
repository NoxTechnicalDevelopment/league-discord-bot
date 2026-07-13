# Security and Reliability Audit — 2026-07-13

## Scope

Reviewed every Discord command, outbound message, Riot API request, and SQLite
operation in `src/`. The focus was untrusted input, database isolation and
integrity, and concurrent scheduled/manual syncs.

## Findings

| Severity | Finding | Evidence | Disposition |
| --- | --- | --- | --- |
| Critical | Cross-server data disclosure | `users`, `matches`, and `ranks` are keyed only by `discord_id`; leaderboard and meme-stat queries read every registered user, then post the result in each guild. | Fix in this change: scope all profiles and derived data to `(guild_id, discord_id)`. Existing registrations cannot be safely assigned to a guild, so the migration deletes the old unscoped cache and members must register again. |
| High | Mention injection in bot output | Riot IDs supplied to `/register` are stored and later interpolated into message and embed content. Default Discord mention parsing can turn a valid-looking identifier such as `@everyone#tag` into a broadcast. Riot error bodies are also reflected to users. | Fix in this change: disable mentions for all bot messages and return generic API errors. |
| High | Riot API path injection | `game_name` and `tag_line` are concatenated directly into an HTTP path. Slash, query, and percent characters can change the request path. | Fix in this change: percent-encode each path segment. |
| High | Concurrent syncs and stale writes | `/syncnow` and the scheduled task can run together. SQLite uses a new connection per call with no busy timeout; a profile can also be re-registered while a sync is writing old-account matches/ranks. | Fix in this change: serialize syncs in-process, configure SQLite busy/WAL settings, use transactional profile replacement, and condition writes on the current PUUID. |
| Medium | Riot API abuse / resource exhaustion | Public lookup commands have no cooldown; every lookup creates API requests, and sync requests have no HTTP timeout. | Fix in this change: add per-user/per-guild cooldowns and a request timeout. |
| Medium | Local database exposure and accidental commits | The database is stored in `data/`, alongside tracked assets, with no ignore rule or restrictive permission setup. It stores Discord IDs, Riot IDs, and PUUIDs. | Fix in this change: ignore runtime secrets/data and set the database mode to owner-only where supported. |
| Medium | Integrity and reporting errors | SQLite schema does not constrain numeric match fields; sync counts every attempted insertion as a new match even when the uniqueness constraint ignores it. | Fix in this change: add schema checks and use the insert result in the summary. |
| Low | Unhandled valid remote-data edge cases | Empty match histories, missing participants, and non-Riot exceptions can escape command handlers and leave the user with an interaction failure. | Fix in this change: handle empty/malformed match data and add a safe application-command error response. |
| Low | Unbounded cache retention | Weekly features only read seven days, but old matches are never removed. | Fix in this change: prune old match rows after a sync. |

## Confirmed non-findings

* SQL statements use parameter binding for all values; no direct SQL injection
  path was found.
* No shell execution, `eval`, or subprocess use is reachable from Discord
  commands.
* Repository-tracked files do not include an `.env`, database, private key, or
  token.

## Validation planned for the patch

* Database tests for guild isolation, stale-write rejection, duplicate-match
  accounting, and old-cache cleanup.
* Linting and the complete test suite.
* A focused review of every outbound message and Riot URL construction site.
