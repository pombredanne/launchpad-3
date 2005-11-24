
set client_min_messages=ERROR;

ALTER TABLE PollOption RENAME COLUMN shortname TO title;

INSERT INTO LaunchpadDatabaseRevision VALUES (25,47,0);
