SET client_min_messages=ERROR;

-- Add a new column in the Archive table pointing to the GpgKey
-- used for sigining.
-- See https://launchpad.canonical.com/SoyuzSignedArchives.

ALTER TABLE Archive
    ADD COLUMN signing_key integer REFERENCES GpgKey(id);

CREATE INDEX archive__signing_key__idx
    ON archive(signing_key) WHERE signing_key IS NOT NULL;


INSERT INTO LaunchpadDatabaseRevision VALUES (121, 86, 0);
