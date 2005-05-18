
/* This patch needs to be rolled out after the next production upgrade.
The sequence is:
    production database upgrade
    run the migration script, stuffing blobs into the librarian
    apply this patch
    startup new launchpad

This patch will not get a real number until rollout.

*/

set client_min_messages=ERROR;

ALTER TABLE POTemplate DROP COLUMN rawfile_;
ALTER TABLE POTemplate ALTER COLUMN rawfile SET NOT NULL;

ALTER TABLE POFile DROP COLUMN rawfile_;
ALTER TABLE POFile ADD CONSTRAINT pofile_rawimportstatus_valid CHECK
    (((rawfile IS NULL) AND (rawimportstatus <> 2)) OR (rawfile IS NOT NULL));

/* Fake number to keep the test suite happy */
INSERT INTO LaunchpadDatabaseRevision VALUES (17, 99, 0);

