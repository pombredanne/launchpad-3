SET client_min_messages=ERROR;

-- drop unused columns due a redesign,
-- related indexes will be removed automatically
ALTER TABLE personalpackagearchive DROP COLUMN packages;
ALTER TABLE personalpackagearchive DROP COLUMN sources;
ALTER TABLE personalpackagearchive DROP COLUMN release;
ALTER TABLE personalpackagearchive DROP COLUMN release_gpg;

INSERT INTO LaunchpadDatabaseRevision VALUES (40, 31, 0);
