SET client_min_messages=ERROR;

ALTER TABLE DistroReleaseQueue ADD COLUMN signingkey INTEGER;
ALTER TABLE DistroReleaseQueue
    ADD CONSTRAINT distroreleasequeue_signingkey_fk
    FOREIGN KEY (signingkey) REFERENCES gpgkey(id);

INSERT INTO LaunchpadDatabaseRevision VALUES (67, 99, 0);

