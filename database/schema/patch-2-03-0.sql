SET client_min_messages TO error;

/* Migrate sourcepackagerelease reference from Binarypackage to Build
    for Soyuz
 */
ALTER TABLE Build ADD COLUMN sourcepackagerelease integer REFERENCES 
    SourcepackageRelease(id);
UPDATE Build 
    SET sourcepackagerelease = Binarypackage.sourcepackagerelease
    FROM Binarypackage
    WHERE Build.id = Binarypackage.build;
ALTER TABLE Build ALTER COLUMN sourcepackagerelease SET NOT NULL;
ALTER TABLE Binarypackage DROP COLUMN sourcepackagerelease;

