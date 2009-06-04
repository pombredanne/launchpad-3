SET client_min_messages = ERROR;

ALTER TABLE BranchJob
  ALTER COLUMN branch DROP NOT NULL;

INSERT INTO LaunchpadDatabaseRevision VALUES (2109, 98, 0);

