SET client_min_messages=ERROR;

-- Fiera buildd changes

-- Builder table needs a speed index

ALTER TABLE Builder ADD COLUMN speedindex INTEGER;

COMMENT ON COLUMN Builder.speedindex IS 'A relative measure of the speed of this builder. If NULL, we do not yet have a speedindex for the builder else it is the number of seconds needed to perform a reference build';

-- Builder table needs a 'known good' flag

ALTER TABLE Builder ADD COLUMN builderok BOOLEAN;
UPDATE Builder SET builderok=true;
ALTER TABLE Builder ALTER COLUMN builderok SET NOT NULL;
ALTER TABLE Builder ADD COLUMN failnotes TEXT;

	
-- We need a build queue table

CREATE TABLE BuildQueue (
  id SERIAL PRIMARY KEY,
  build INTEGER REFERENCES build(id) NOT NULL,
  builder INTEGER REFERENCES builder(id),
  created TIMESTAMP WITH TIME ZONE NOT NULL,
  buildstart TIMESTAMP WITH TIME ZONE,
  logtail TEXT
);

UPDATE LaunchpadDatabaseRevision SET major=6, minor=31, patch=0;

