ALTER TABLE BugBranch
    ALTER COLUMN status DROP NOT NULL;

INSERT INTO LaunchpadDatabaseRevision VALUES (2109, 99, 0);
