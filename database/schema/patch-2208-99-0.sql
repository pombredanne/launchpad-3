SET client_min_messages=ERROR;

ALTER TABLE SourcePackageRelease ADD COLUMN debversion_sort_key TEXT;
ALTER TABLE BinaryPackageRelease ADD COLUMN debversion_sort_key TEXT;

UPDATE SourcePackageRelease 
    SET debversion_sort_key = debversion_sort_key(version);
UPDATE BinaryPackageRelease 
    SET debversion_sort_key = debversion_sort_key(version);

/* Is there a quicker way of migrating the index data? */
DROP INDEX binarypackagerelease_version_sort;
DROP INDEX sourcepackagerelease_version_sort;

CREATE INDEX SourcePackageRelease__debversion_sort_key__idx
    ON SourcePackageRelease(debversion_sort_key);
CREATE INDEX BinaryPackageRelease__debversion_sort_key__idx
    ON BinaryPackageRelease(debversion_sort_key);

/* This patch can't land with these lines without appropriate code
 * changes.
 */
ALTER TABLE SourcePackageRelease
    ALTER COLUMN debversion_sort_key not null;
ALTER TABLE BinaryPackageRelease
    ALTER COLUMN debversion_sort_key not null;

INSERT INTO LaunchpadDatabaseRevision VALUES (2208, 25, 0);
