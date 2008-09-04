SET client_min_messages=ERROR;

CREATE TABLE ArchiveAuthToken (
    id serial PRIMARY KEY,
    date_created timestamp without time zone
        DEFAULT (CURRENT_TIMESTAMP AT TIME ZONE 'UTC') NOT NULL,
    date_expires timestamp without time zone,
    archive integer NOT NULL REFERENCES Archive(id),
    token text UNIQUE NOT NULL,
    description text
);

CREATE INDEX archiveauthtoken__archive__idx
    ON archiveauthtoken
    USING btree(archive);

CREATE INDEX archiveauthtoken__date_expires__idx
    ON archiveauthtoken (date_expires)
    WHERE date_expires IS NOT NULL;

ALTER TABLE Archive
    ADD COLUMN dirty_tokens boolean NOT NULL DEFAULT FALSE;

INSERT INTO LaunchpadDatabaseRevision VALUES (121, 99, 0);
