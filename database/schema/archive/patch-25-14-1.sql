set client_min_messages=ERROR;

CREATE INDEX pofile_latestsubmission_idx ON POFile(latestsubmission);

UPDATE POFile SET latestsubmission=NULL WHERE latestsubmission IS NOT NULL AND latestsubmission not in (select id from posubmission where id=pofile.latestsubmission);

ALTER TABLE POFile ADD CONSTRAINT pofile_latestsubmission_fk FOREIGN KEY (latestsubmission) REFERENCES POSubmission;

INSERT INTO LaunchpadDatabaseRevision VALUES (25, 14, 1);
