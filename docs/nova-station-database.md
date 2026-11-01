# Nova Station database

Nova Station uses the Paradise SQL schema for database-backed staff accounts, bans, library records, and changelog data. The changelog table is intentionally left empty unless Nova Station staff explicitly provide entries.

The live server uses the local MariaDB service and a dedicated `nova_station_app` account. Keep MariaDB bound to loopback and do not commit `config/config.toml` or its password. `config/example/config.toml` contains a placeholder only.

For a fresh database, import `SQL/paradise_schema.sql`, then apply `SQL/updates/73-74.sql`. For an existing Paradise database, back it up and apply the migration only. Keep `sql_version` synchronized with `SQL_VERSION` in `code/__DEFINES/misc_defines.dm`.

The `player_access_flags` table stores admin-granted `head_job_whitelist` and `job_playtime_override` entries. Admins with `R_ADMIN` can grant or revoke either flagâ€”or click **Unlock All Jobs & Time Locks**â€”from the **Admin -> Unlock Player Jobs** verb, the **Player Panel (`F7`)**, or a player's **`PP`** options window to immediately unlock Head-of-Staff roles and bypass job/special-role playtime and account-age locks for the selected player.