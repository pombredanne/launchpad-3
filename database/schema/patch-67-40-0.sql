SET client_min_messages=ERROR;

-- Mark which tags have been officially endorsed by a project or
-- distribution.
ALTER TABLE Product ADD COLUMN official_bug_tags TEXT;
ALTER TABLE Distribution ADD COLUMN official_bug_tags TEXT;

INSERT INTO LaunchpadDatabaseRevision VALUES (67, 40, 0);

