SET client_min_messages = ERROR;

ALTER TABLE Branch
  ADD COLUMN size_on_disk BIGINT;

INSERT INTO LaunchpadDatabaseRevision VALUES (2109, 57, 0);

