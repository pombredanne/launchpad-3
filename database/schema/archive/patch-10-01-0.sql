/*
 * Fiera needs various changes to the database
 */

SET client_min_messages=ERROR;

ALTER TABLE DistroArchRelease ADD COLUMN chroot INTEGER;
ALTER TABLE DistroArchRelease ADD CONSTRAINT distroarchrelease_chroot_fk
      FOREIGN KEY (chroot) REFERENCES LibraryFileAlias(id);


INSERT INTO LaunchpadDatabaseRevision VALUES (10,1,0);

