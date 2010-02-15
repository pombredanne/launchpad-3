SET client_min_messages=ERROR;

ALTER TABLE SourcePackageRecipeBuild ADD COLUMN dependencies text;
ALTER TABLE SourcePackageRecipeBuild ADD COLUMN pocket integer
    DEFAULT 0 NOT NULL;
ALTER TABLE SourcePackageRecipeBuild ADD COLUMN upload_log integer
    CONSTRAINT sourcepackagerecipebuild__upload_log__fk
    REFERENCES LibraryFileAlias;

CREATE INDEX sourcepackagerecipebuild__upload_log__idx
    ON SourcePackageRecipeBuild(upload_log) WHERE upload_log IS NOT NULL;

-- We can't drop tables in DB patches due to Slony-I limitations, so
-- we give them a magic name for database/schema/upgrade.py to deal
-- with correctly.
ALTER TABLE SourcePackageRecipeBuildUpload SET SCHEMA todrop; 

INSERT INTO LaunchpadDatabaseRevision VALUES (2207, 32, 0);
