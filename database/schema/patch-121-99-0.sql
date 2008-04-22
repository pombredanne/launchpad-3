SET client_min_messages=ERROR;

ALTER TABLE distroarchseries RENAME COLUMN ppa_supported TO supports_virtualized;

INSERT INTO LaunchpadDatabaseRevision VALUES (121, 99, 0);
