/* Move the srcpackageformat column to where it really belongs */

begin transaction;

ALTER TABLE SourcePackageRelease DROP COLUMN srcpackageformat;
ALTER TABLE SourcePackage ADD COLUMN srcpackageformat INTEGER;

UPDATE SourcePackage
SET srcpackageformat = 1;

ALTER TABLE SourcePackage ALTER COLUMN srcpackageformat SET NOT NULL;

COMMENT ON COLUMN SourcePackage.srcpackageformat IS 'The format of this source package, e.g. DPKG, RPM, EBUILD, etc.';

commit transaction;