SET client_min_messages=ERROR;

-- Make Branch title and summary nullable. Branches create by sftp-pushing to
-- the supermirror have no title or summary.

ALTER TABLE Branch ALTER COLUMN title DROP NOT NULL;
ALTER TABLE Branch ALTER COLUMN summary DROP NOT NULL;

INSERT INTO LaunchpadDatabaseRevision VALUES (40, 24, 0);
