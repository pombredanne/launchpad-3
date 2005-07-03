
/* Add a field to give the user a possibility to provide bug task
   specific information. */
ALTER TABLE BugTask ADD COLUMN statusexplanation TEXT;

INSERT INTO LaunchpadDatabaseRevision VALUES (17, 26, 0);

