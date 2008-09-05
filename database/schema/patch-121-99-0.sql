SET client_min_messages=ERROR;

-- A table for requesting and recording the existence of private
-- GPG keys hosted by Launchpad.

CREATE TABLE PrivateGpgKey (
    id serial PRIMARY KEY,
    date_requested timestamp without time zone
        DEFAULT (CURRENT_TIMESTAMP AT TIME ZONE 'UTC') NOT NULL,
    requestor integer NOT NULL REFERENCES Person(id),
    comment text,
    status integer,
    gpg_key integer UNIQUE REFERENCES GpgKey(id),
    date_created timestamp without time zone
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
