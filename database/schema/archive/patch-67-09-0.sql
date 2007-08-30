SET client_min_messages = ERROR;

/* These indexes allow queries on SourcepackageRelease and BinarypackageRelease
to be ordered by their version efficiently:

    SELECT * FROM SourcepackageRelease
    ORDER BY debversion_sort_key(version);
*/

CREATE INDEX sourcepackagerelease_version_sort
    ON SourcepackageRelease(debversion_sort_key(version));
CREATE INDEX binarypackagerelease_version_sort
    ON BinarypackageRelease(debversion_sort_key(version));

INSERT INTO LaunchpadDatabaseRevision VALUES (67, 9, 0);
