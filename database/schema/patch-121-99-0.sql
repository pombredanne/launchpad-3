SET client_min_messages=ERROR;

-- Add a new column in the Archive table pointing to the GpgKey
-- used for sigining.
-- See https://launchpad.canonical.com/SoyuzSignedArchives.

ALTER TABLE Archive
    ADD COLUMN gpg_key integer REFERENCES GpgKey(id);

CREATE INDEX archive__gpg_key__idx
    ON archive(gpg_key) WHERE gpg_key IS NOT NULL;


INSERT INTO LaunchpadDatabaseRevision VALUES (121, 99, 0);
