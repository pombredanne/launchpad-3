
/*
  We will start automatically trying to import the SourceSource, and will
  advise the admins and the requester what the status of that is when we
  try it. STUB: this is not yet done.
*/

ALTER TABLE SourceSource ADD COLUMN autotested integer;
ALTER TABLE SourceSource ALTER COLUMN autotested SET DEFAULT 0;
UPDATE SourceSource SET autotested = 0;
ALTER TABLE SourceSource ALTER COLUMN autotested SET NOT NULL;

COMMENT ON COLUMN SourceSource.autotested IS 'This flag gives the results of an automatic attempt to import the revision control repository.';

ALTER TABLE SourceSource ADD COLUMN datestarted timestamp without time zone;
ALTER TABLE SourceSource ALTER COLUMN datestarted SET DEFAULT (CURRENT_TIMESTAMP AT TIME ZONE 'UTC');

COMMENT ON COLUMN SourceSource.datestarted IS 'The timestamp of the last time an import or sync was started on this sourcesource.';

ALTER TABLE SourceSource ADD COLUMN datefinished timestamp without time zone;
ALTER TABLE SourceSource ALTER COLUMN datefinished SET DEFAULT (CURRENT_TIMESTAMP AT TIME ZONE 'UTC');

COMMENT ON COLUMN SourceSource.datefinished IS 'The timestamp of the last time an import or sync finished on this sourcesource.';

UPDATE LaunchpadDatabaseRevision SET major=5, minor=4, patch=0;

