SET client_min_messages=ERROR;

ALTER TABLE POSubmission ALTER COLUMN person SET NOT NULL;

-- We should migrate data before we add this constraint.
ALTER TABLE POSubmission
ADD CONSTRAINT posubmission_just_one_submission_for_potranslation
UNIQUE(potranslation, pomsgset, pluralform);

-- This index is now unnecessary
DROP INDEX posubmission_potranslation_idx;

INSERT INTO LaunchpadDatabaseRevision VALUES (67, 01, 1);
