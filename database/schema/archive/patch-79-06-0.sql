SET client_min_messages=ERROR;

ALTER TABLE DistroReleaseQueue
    ADD COLUMN signing_key INTEGER REFERENCES GPGKey;

INSERT INTO LaunchpadDatabaseRevision VALUES (79, 6, 0);
