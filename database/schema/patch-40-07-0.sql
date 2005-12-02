SET client_min_messages=ERROR;

CREATE TABLE ShipitReport (
    id              serial PRIMARY KEY,
    datecreated     timestamp without time zone NOT NULL,
    csvfile         integer NOT NULL REFERENCES LibraryFileAlias(id)
);

CREATE TABLE Continent (
    id              serial PRIMARY KEY,
    code            text NOT NULL UNIQUE,
    name            text NOT NULL UNIQUE
);

ALTER TABLE Country ADD COLUMN continent integer REFERENCES Continent(id);
ALTER TABLE CountrY ALTER COLUMN continent SET NOT NULL;

INSERT INTO LaunchpadDatabaseRevision VALUES (40, 07, 0);
