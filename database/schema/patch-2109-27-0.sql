SET client_min_messages=ERROR;

CREATE TABLE ParsedLibrarianApacheLog (
    id serial PRIMARY KEY,
    file_name text NOT NULL,
    first_line_timestamp TIMESTAMP WITHOUT TIME ZONE,
    bytes_read integer NOT NULL);

ALTER TABLE LibraryFileAlias ADD COLUMN hits INTEGER NOT NULL DEFAULT 0;

INSERT INTO LaunchpadDatabaseRevision VALUES (2109, 27, 0);

