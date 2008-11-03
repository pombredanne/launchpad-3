SET client_min_messages=ERROR;

ALTER TABLE Branch
  ADD COLUMN branch_format integer,
  ADD COLUMN repository_format integer,
  ADD COLUMN metadir_format integer;

INSERT INTO LaunchpadDatabaseRevision VALUES (121, 44, 0);
