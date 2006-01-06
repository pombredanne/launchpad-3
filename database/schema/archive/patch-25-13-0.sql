SET client_min_messages=ERROR;

CREATE INDEX person_karma_idx ON Person(karma);

INSERT INTO LaunchpadDatabaseRevision VALUES (25, 13, 0);

