SET client_min_messages=ERROR;

ALTER TABLE Distribution ADD COLUMN archiveadmin integer;

ALTER TABLE Distribution ADD CONSTRAINT distribution_archiveadmin_fk
      FOREIGN KEY (archiveadmin) REFERENCES Person;


INSERT INTO LaunchpadDatabaseRevision VALUES (40, 99, 0);

