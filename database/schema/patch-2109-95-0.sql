SET client_min_messages = ERROR;

ALTER TABLE Branch
  ADD COLUMN size_on_disk INT;

INSERT INTO LaunchpadDatabaseRevision VALUES (2109, 95, 0);

