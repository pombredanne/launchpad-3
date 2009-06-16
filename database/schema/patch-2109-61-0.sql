/* TODO: When I try to drop the column altogether, I get an sql error.  This
   patch should really just drop the column.
*/
ALTER TABLE BugBranch
    ALTER COLUMN status DROP NOT NULL;

INSERT INTO LaunchpadDatabaseRevision VALUES (2109, 99, 0);
