/* Ensure a bug is not a duplicate of itself */
ALTER TABLE Bug ADD CONSTRAINT notduplicateofself CHECK (not id = duplicateof);

/* BugSystem names must be lower case */
ALTER TABLE BugSystem ADD CHECK (name = lower(name));

/* Soyuz changes for Soyuz */
ALTER TABLE SourcePackage RENAME title TO shortdesc;
ALTER TABLE SourcePackage DROP name;
ALTER TABLE SourcePackage ADD COLUMN sourcepackagename integer 
    REFERENCES SourcePackageName;
ALTER TABLE SourcePackage ALTER COLUMN sourcepackagename SET NOT NULL;

