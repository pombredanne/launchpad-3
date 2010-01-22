SET client_min_messages=ERROR;

ALTER TABLE SourcePackageRecipeBuild ADD COLUMN dependencies text;
ALTER TABLE SourcePackageRecipeBuild ADD COLUMN pocket integer DEFAULT 0 NOT NULL;
ALTER TABLE SourcePackageRecipeBuild ADD COLUMN upload_log integer REFERENCES LibraryFileAlias;

INSERT INTO LaunchpadDatabaseRevision VALUES (2207, 99, 0);
