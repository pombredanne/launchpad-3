SET client_min_messages=ERROR;

ALTER TABLE POSubmission ALTER COLUMN person SET NOT NULL;

-- We should migrate data before we add this constraint.
ALTER TABLE POSubmission
ADD CONSTRAINT posubmission_just_one_submission_for_potranslation
UNIQUE(pomsgset, pluralform, potranslation);

INSERT INTO LaunchpadDatabaseRevision VALUES (40, 53, 0);
