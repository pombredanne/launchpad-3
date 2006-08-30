SET client_min_messages=ERROR;

/* Don't allow filenames to contain a / character as the Librarian cannot
serve them, and if it did could be used for (probably lame) social
engineering attacks.
*/
UPDATE LibraryFileAlias SET filename=replace(filename, '/', '_')
    WHERE filename LIKE '%/%';
ALTER TABLE LibraryFileAlias
    ADD CONSTRAINT valid_filename CHECK (filename NOT LIKE '%/%');

INSERT INTO LaunchpadDatabaseRevision VALUES (67, 12, 0);

