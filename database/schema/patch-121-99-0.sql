SET client_min_messages=ERROR;

CREATE TABLE ArchiveSubscriber (
    id serial PRIMARY KEY,
    archive integer NOT NULL REFERENCES Archive(id),
    registrant integer NOT NULL REFERENCES Person(id),
    date_created timestamp without time zone
        DEFAULT (CURRENT_TIMESTAMP AT TIME ZONE 'UTC') NOT NULL,
    subscriber integer NOT NULL REFERENCES Person(id),
    date_expires timestamp without time zone,
    status integer NOT NULL,
    description text,
    date_cancelled timestamp without time zone,
    cancelled_by integer REFERENCES Person(id)
);
    
CREATE INDEX archivesubscriber__archive__idx
    ON archivesubscriber (archive);

CREATE INDEX archivesubscriber__date_expires__idx
    ON archivesubscriber (date_expires)
    WHERE date_expires IS NOT NULL;

CREATE INDEX archivesubscriber__date_created__idx
    ON archivesubscriber (date_created);


CREATE TABLE ArchiveAuthToken (
    id serial PRIMARY KEY,
    archive integer NOT NULL REFERENCES Archive(id),
    person integer NOT NULL REFERENCES Person(id),
    date_created timestamp without time zone
        DEFAULT (CURRENT_TIMESTAMP AT TIME ZONE 'UTC') NOT NULL,
    date_revoked timestamp without time zone,
    token text UNIQUE NOT NULL
);

CREATE INDEX archiveauthtoken__archive__idx
    ON ArchiveAuthToken (archive);

CREATE INDEX archiveauthtoken__person__idx
    ON ArchiveAuthToken (person);

CREATE INDEX archiveauthtoken__date_created__idx
    ON ArchiveAuthToken (date_created);


ALTER TABLE Archive
    ADD COLUMN dirty_tokens boolean NOT NULL DEFAULT FALSE;

INSERT INTO LaunchpadDatabaseRevision VALUES (121, 99, 0);
