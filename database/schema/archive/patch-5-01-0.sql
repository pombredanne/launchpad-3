SET client_min_messages=ERROR;
--
-- The BinaryPackage uniqueness constraints are wrong. Correct them
--

ALTER TABLE BinaryPackage 
    DROP CONSTRAINT "binarypackage_binarypackagename_key";

ALTER TABLE BinaryPackage
    ADD CONSTRAINT "binarypackage_binarypackagename_key" 
        UNIQUE(binarypackagename,build,version);

UPDATE LaunchpadDatabaseRevision SET major=5, minor=1, patch=0;

