SET client_min_messages=ERROR;

CREATE TABLE BzrFormat
(
  id serial PRIMARY KEY,
  name TEXT NOT NULL UNIQUE
);

ALTER TABLE Branch
  ADD COLUMN branch_format integer REFERENCES BzrFormat;

ALTER TABLE Branch
  ADD COLUMN repository_format integer REFERENCES BzrFormat;

-- We may want to aggregate these for statistics, but unlikely
-- to need to do this for normal UI interaction.

INSERT INTO LaunchpadDatabaseRevision VALUES (121, 99, 0);
