--
-- The BinaryPackage uniqueness constraints are wrong. Correct them
--

ALTER TABLE BinaryPackage 
    DROP CONSTRAINT "binarypackage_binarypackagename_key";

ALTER TABLE BinaryPackage
    ADD CONSTRAINT "binarypackage_binarypackagename_key" 
        UNIQUE(binarypackagename,build,version);
