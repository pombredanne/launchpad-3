SET client_min_messages=ERROR;

ALTER TABLE Bug
ADD COLUMN hotness INTEGER NOT NULL DEFAULT 0;

ALTER TABLE BugTask
ADD COLUMN hotness_rank INTEGER NOT NULL DEFAULT 0;

CREATE INDEX bug__hotness__idx ON Bug USING btree (hotness);

INSERT INTO LaunchpadDatabaseRevision VALUES (2109, 25, 0);
