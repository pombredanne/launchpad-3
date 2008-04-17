SET client_min_messages=ERROR;

ALTER TABLE Branch
  ADD COLUMN branch_format TEXT;

ALTER TABLE Branch
  ADD COLUMN repository_format TEXT;

-- We may want to aggregate these for statistics, but unlikely
-- to need to do this for normal UI interaction.

INSERT INTO LaunchpadDatabaseRevision VALUES (121, 99, 0);
