-- Fiera buildd changes

-- Builder table needs a speed index

ALTER TABLE Builder ADD COLUMN speedindex INTEGER;

COMMENT ON COLUMN Builder.speedindex IS 'A relative measure of the speed of this builder. If NULL, we do not yet have a speedindex for the builder else it is the number of seconds needed to perform a reference build';

-- Builder table needs a 'known good' flag

ALTER TABLE Builder ADD COLUMN builderok BOOLEAN;
UPDATE Builder SET builderok=true;
ALTER TABLE Builder ALTER COLUMN builderok SET NOT NULL;
ALTER TABLE Builder ADD COLUMN failnotes TEXT;

COMMENT ON COLUMN Builder.builderok IS 'Should a builder fail for any reason, from out-of-disk-space to not responding to the buildd master, the builderok flag is set to false and the failnotes column is filled with a reason.';
COMMENT ON COLUMN Builder.failnotes IS 'This column gets filled out with a textual description of how/why a builder has failed. If the builderok column is true then the value in this column is irrelevant and should be treated as NULL or empty.';
	
-- We need a build queue table

CREATE TABLE BuildQueue (
  id SERIAL PRIMARY KEY,
  build INTEGER REFERENCES build(id) NOT NULL,
  builder INTEGER REFERENCES builder(id),
  created TIMESTAMP WITH TIME ZONE NOT NULL,
  buildstart TIMESTAMP WITH TIME ZONE,
  logtail TEXT
);

COMMENT ON TABLE BuildQueue IS 'BuildQueue: The queue of builds in progress/scheduled to run. This table is the core of the build daemon master. It lists all builds in progress or scheduled to start.';
COMMENT ON COLUMN BuildQueue.build IS 'The build for which this queue item exists. This is how the buildd master will find all the files it needs to perform the build';
COMMENT ON COLUMN BuildQueue.builder IS 'The builder assigned to this build. Some builds will have a builder assigned to queue them up; some will be building on the specified builder already; others will not have a builder yet (NULL) and will be waiting to be assigned into a builder''s queue';
COMMENT ON COLUMN BuildQueue.created IS 'The timestamp of the creation of this row. This is used by the buildd master scheduling algorithm to decide how soon to schedule a build to run on a given builder.';
COMMENT ON COLUMN BuildQueue.buildstart IS 'The timestamp of the start of the build run on the given builder. If this is NULL then the build is not running yet.';
COMMENT ON COLUMN BuildQueue.logtail IS 'The tail end of the log of the current build. This is updated regularly as the buildd master polls the buildd slaves. Once the build is complete; the full log will be lodged with the librarian and linked into the build table.';

