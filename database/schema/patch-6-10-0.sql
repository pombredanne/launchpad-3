/* Add an 'autoupdate' column to Product */
ALTER TABLE Product ADD COLUMN autoupdate BOOLEAN;
UPDATE Product SET autoupdate = False;
ALTER TABLE Product ALTER COLUMN autoupdate SET DEFAULT FALSE;

UPDATE LaunchpadDatabaseRevision SET major=6,minor=10,patch=0;

