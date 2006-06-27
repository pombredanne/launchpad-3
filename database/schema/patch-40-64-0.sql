SET client_min_messages=ERROR;

ALTER TABLE Distribution DROP COLUMN uploadadmin;
ALTER TABLE Distribution DROP COLUMN uploadsender;

ALTER TABLE Distribution ADD COLUMN upload_admin integer;
ALTER TABLE Distribution ADD COLUMN upload_sender text;

ALTER TABLE Distribution ADD CONSTRAINT distribution_upload_admin_fk
      FOREIGN KEY (upload_admin) REFERENCES Person;


INSERT INTO LaunchpadDatabaseRevision VALUES (40, 64, 0);

