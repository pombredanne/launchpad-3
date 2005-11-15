/*
 * Add a .changes column to the upload queue table
 */

SET client_min_messages = ERROR;

ALTER TABLE DistroReleaseQueue ADD COLUMN changesfile TEXT;
ALTER TABLE DistroReleaseQueue ALTER COLUMN changesfile SET NOT NULL;

INSERT INTO LaunchpadDatabaseRevision VALUES (25,99,0);
