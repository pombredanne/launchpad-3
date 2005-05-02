SET client_min_messages=ERROR;

ALTER TABLE Karma RENAME COLUMN karmafield TO karmatype;

INSERT INTO LaunchpadDatabaseRevision VALUES (11, 11, 0);
