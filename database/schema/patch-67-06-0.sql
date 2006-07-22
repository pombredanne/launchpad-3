SET client_min_messages=ERROR;

ALTER TABLE pocketchroot DROP CONSTRAINT pocketchroot_chroot_key;

INSERT INTO LaunchpadDatabaseRevision VALUES (67, 6, 0);
