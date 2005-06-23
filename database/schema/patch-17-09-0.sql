
SET client_min_messages=ERROR;

ALTER TABLE POTemplate ALTER COLUMN rawfile DROP NOT NULL;
ALTER TABLE POTemplate RENAME COLUMN rawfile to rawfile_;
ALTER TABLE POTemplate ADD COLUMN rawfile integer REFERENCES
	LibraryFileAlias;

ALTER TABLE POFile DROP CONSTRAINT pofile_rawimportstatus_valid;
ALTER TABLE POFile RENAME COLUMN rawfile to rawfile_;
ALTER TABLE POFile ADD COLUMN rawfile integer REFERENCES
	LibraryFileAlias;

INSERT INTO LaunchpadDatabaseRevision VALUES (17, 9, 0);

