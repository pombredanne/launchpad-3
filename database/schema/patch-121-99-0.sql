SET client_min_messages=ERROR;

-- A table for requesting and storing private GPG keys.

CREATE TABLE PrivateGpgKey (
    id serial PRIMARY KEY,
    date_created timestamp without time zone
        DEFAULT (CURRENT_TIMESTAMP AT TIME ZONE 'UTC') NOT NULL,
    owner integer NOT NULL REFERENCES Person(id),
    gpg_key integer UNIQUE REFERENCES GpgKey(id),
    status integer,
    comment text
);


-- A table for selecting a private GPG key that should be used for
-- sigining a archive.

CREATE TABLE ArchiveSigningKey (
    id serial PRIMARY KEY,
    date_created timestamp without time zone
        DEFAULT (CURRENT_TIMESTAMP AT TIME ZONE 'UTC') NOT NULL,
    archive integer UNIQUE NOT NULL REFERENCES Archive(id),
    gpg_key integer NOT NULL REFERENCES GpgKey(id)
);


INSERT INTO LaunchpadDatabaseRevision VALUES (121, 99, 0);
