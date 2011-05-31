SET client_min_messages=ERROR;

CREATE INDEX person__displayname__idx ON Person(lower(displayname));

INSERT INTO LaunchpadDatabaseRevision VALUES (2208, 99, 0);
