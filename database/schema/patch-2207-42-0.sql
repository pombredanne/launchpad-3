SET client_min_messages=ERROR;

ALTER TABLE BugWatch ADD COLUMN next_check timestamp without time zone DEFAULT timezone('UTC'::text, now());

CREATE INDEX bugwatch__next_check__idx ON BugWatch(next_check);

INSERT INTO LaunchpadDatabaseRevision VALUES (2207, 42, 0);
