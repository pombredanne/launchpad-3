SET client_min_messages=ERROR;

ALTER TABLE BugTracker ADD COLUMN block_comment_pushing BOOLEAN NOT NULL
    DEFAULT false;

INSERT INTO LaunchpadDatabaseRevision VALUES (121, 37, 0);
