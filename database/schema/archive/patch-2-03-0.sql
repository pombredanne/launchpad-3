SET client_min_messages TO error;

/* Migrate sourcepackagerelease reference from BinaryPackage to Build
    for Soyuz
 */
ALTER TABLE Build ADD COLUMN sourcepackagerelease integer REFERENCES 
    SourcePackageRelease(id);
UPDATE Build 
    SET sourcepackagerelease = BinaryPackage.sourcepackagerelease
    FROM BinaryPackage
    WHERE Build.id = BinaryPackage.build;
ALTER TABLE Build ALTER COLUMN sourcepackagerelease SET NOT NULL;
ALTER TABLE BinaryPackage DROP COLUMN sourcepackagerelease;

