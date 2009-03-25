SET client_min_messages=ERROR;

CREATE TABLE LibraryFileDownloadCount (
    id serial PRIMARY KEY,
    libraryfilealias integer NOT NULL
        CONSTRAINT libraryfiledownloadcount__libraryfilealias__fk
        REFERENCES LibraryFileAlias
        ON DELETE CASCADE,
    day date NOT NULL,
    country INTEGER REFERENCES country(id),
    count integer NOT NULL,
    CONSTRAINT libraryfiledownloadcount__libraryfilealias__day__country__key
        UNIQUE (libraryfilealias, day, country)
    );

INSERT INTO LaunchpadDatabaseRevision VALUES (2109, 19, 0);

