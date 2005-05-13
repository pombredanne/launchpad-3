SET client_min_messages=ERROR;

/*
 * Build Queue had 'with time zone' timestamps
 */

ALTER TABLE BuildQueue DROP COLUMN created;
ALTER TABLE BuildQueue DROP COLUMN buildstart;

ALTER TABLE BuildQueue ADD COLUMN created TIMESTAMP WITHOUT TIME ZONE;
ALTER TABLE BuildQueue ADD COLUMN buildstart TIMESTAMP WITHOUT TIME ZONE;

UPDATE BuildQueue SET created=CURRENT_TIMESTAMP AT TIME ZONE 'UTC';
ALTER TABLE BuildQueue ALTER COLUMN created SET NOT NULL;


/*
 * By storing the last known score of a build queue item we can
 * guage some idea of where it is in the queue
 */

ALTER TABLE BuildQueue ADD COLUMN lastscore INTEGER;

INSERT INTO LaunchpadDatabaseRevision VALUES (17, 1, 0);
