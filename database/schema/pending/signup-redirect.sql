SET client_min_messages=ERROR;

ALTER TABLE LoginToken ADD COLUMN redirectionurl text;

INSERT INTO LaunchpadDatabaseRevision VALUES (40, 66, 0);

