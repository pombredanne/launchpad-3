/*
Add a signature file to productreleasefile.
*/

SET client_min_messages=ERROR;

ALTER TABLE ProductReleaseFile ADD COLUMN signature INTEGER;
ALTER TABLE ProductReleaseFile
    ADD CONSTRAINT productreleasefile__signature__fk
    FOREIGN KEY (signature) REFERENCES LibraryFileAlias;
CREATE INDEX productreleasefile__signature__idx
    ON ProductReleaseFile (signature) WHERE signature IS NOT NULL;

INSERT INTO LaunchpadDatabaseRevision VALUES (88, 40, 0);
