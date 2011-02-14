SET client_min_messages=ERROR;

-- This index is getting bloated, and is mostly NULL.
ALTER TABLE Bug DROP CONSTRAINT bug_name_key;
CREATE UNIQUE INDEX bug__name__key ON Bug (name) WHERE name IS NOT NULL;

-- This table is huge and append only
ALTER TABLE BranchRevision SET (fillfactor=100);

INSERT INTO LaunchpadDatabaseRevision VALUES (2208, 42, 0);

