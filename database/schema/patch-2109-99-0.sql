SET client_min_messages=ERROR;

-- Mode for importing translations for this series from a branch in 
-- codehosting.

ALTER TABLE ProductSeries
  ADD COLUMN translations_sync integer NOT NULL DEFAULT 0;

INSERT INTO LaunchpadDatabaseRevision VALUES (2109, 99, 0);

