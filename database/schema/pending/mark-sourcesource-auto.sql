
/*
  We will start automatically trying to import the SourceSource, and will
  advise the admins and the requester what the status of that is when we
  try it.
*/

ALTER TABLE SourceSource ADD COLUMN autotested BOOLEAN;

COMMENT ON COLUMN SourceSource.autotested IS 'This flag gives the results of an automatic attempt to import the revision control repository.';

