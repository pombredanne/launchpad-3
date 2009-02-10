SET client_min_messages=ERROR;

ALTER TABLE BugTask
ADD COLUMN hotness INTEGER NOT NULL DEFAULT 0,
ADD COLUMN hotness_rank INTEGER NOT NULL DEFAULT 0;

CREATE INDEX bugtask__hotness__idx ON BugTask USING btree (hotness);

INSERT INTO LaunchpadDatabaseRevision VALUES (2109, 99, 0);
