/* Move the srcpackageformat column to where it really belongs */

/* begin transaction; Don't want this - makes rollout to production harder */

ALTER TABLE SourcePackageRelease DROP COLUMN srcpackageformat;
ALTER TABLE SourcePackage ADD COLUMN srcpackageformat INTEGER;

UPDATE SourcePackage SET srcpackageformat = 1;

ALTER TABLE SourcePackage ALTER COLUMN srcpackageformat SET NOT NULL;


/* commit transaction; */

