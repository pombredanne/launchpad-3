SET client_min_messages=ERROR;

ALTER TABLE Distribution DROP COLUMN uploadadmin;

ALTER TABLE Distribution ADD COLUMN uploadadmin integer;

ALTER TABLE Distribution ADD CONSTRAINT distribution_uploadadmin_fk
      FOREIGN KEY (uploadadmin) REFERENCES Person;


INSERT INTO LaunchpadDatabaseRevision VALUES (40, 99, 0);

