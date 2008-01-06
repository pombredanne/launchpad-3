/*
Set the rcstype to BZR for all product series that have specified
a user_branch (not an import one).

NOTE: user_branch and import_branch will be merged once the new
      code import system is in place on the front end.
*/

SET client_min_messages=ERROR;

UPDATE ProductSeries
SET rcstype = 10
WHERE user_branch IS NOT NULL;

INSERT INTO LaunchpadDatabaseRevision VALUES (88, 66, 0);
