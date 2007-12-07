/*
Add a signature file to productreleasefile.
*/

SET client_min_messages=ERROR;

ALTER TABLE productreleasefile
    ADD COLUMN signaturefile INTEGER;

INSERT INTO LaunchpadDatabaseRevision VALUES (88, 99, 0);
