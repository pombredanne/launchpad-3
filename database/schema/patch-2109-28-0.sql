SET client_min_messages=ERROR;

CREATE TABLE ParsedApacheLog (
    id serial PRIMARY KEY,

    -- First line of the log file, smashed to ASCII. This uniquely
    -- identifies the log file, even if its filename is changed
    -- by log rotation or archival.
    first_line text NOT NULL,

    -- How many bytes of the possibly live logfile have been
    -- successfully parsed so far.
    bytes_read integer NOT NULL,

    -- Last time we read some new information from this log file.
    date_last_parsed timestamp WITHOUT TIME ZONE NOT NULL DEFAULT (
        CURRENT_TIMESTAMP AT TIME ZONE 'UTC'));

CREATE INDEX parsedapachelog__first_line__idx ON ParsedApacheLog(first_line);

ALTER TABLE LibraryFileAlias ADD COLUMN hits INTEGER NOT NULL DEFAULT 0;

INSERT INTO LaunchpadDatabaseRevision VALUES (2109, 28, 0);
