SET client_min_messages=ERROR;

-- The level of importing of translations for this series from a branch in 
-- codehosting. Could be "No import", "POT files only", "POT and POT files"

ALTER TABLE ProductSeries
  ADD COLUMN translations_autoimport_level integer NOT NULL DEFAULT 1;

INSERT INTO LaunchpadDatabaseRevision VALUES (2109, 99, 0);

