set client_min_messages=ERROR;

ALTER TABLE BinaryPackageRelease ADD CONSTRAINT
binarypackagerelease_build_name_uniq UNIQUE (build, binarypackagename);

INSERT INTO LaunchpadDatabaseRevision VALUES (25, 44, 0);
