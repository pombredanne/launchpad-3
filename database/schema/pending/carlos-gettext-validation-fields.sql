ALTER TABLE POSubmission ADD COLUMN validationstatus integer;
UPDATE POSubmission SET validationstatus=0;
ALTER TABLE POSubmission ALTER COLUMN validationstatus SET NOT NULL;
ALTER TABLE POSubmission ALTER COLUMN validationstatus SET DEFAULT 0;


COMMENT ON COLUMN POSubmission.validationstatus IS 'Says whether or not we have validated this translation. Its value will be drove by dbschema.TranslationValidationStatus being 0 the value that says this row has not been validated yet.';


INSERT INTO LaunchpadDatabaseRevision VALUES  (17, 99, 0);
