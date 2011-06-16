-- Copyright 2011 Canonical Ltd.  This software is licensed under the
-- GNU Affero General Public License version 3 (see the file LICENSE).

SET client_min_messages=ERROR;

CREATE TABLE BinaryPackagePaths (
    id serial PRIMARY KEY,
    path text
);

CREATE TABLE BinaryPackageReleaseContents (
    binarypackagerelease integer REFERENCES BinaryPackageRelease,
    path integer REFERENCES BinaryPackagePaths,
    PRIMARY KEY (binarypackagerelease, path)
);

INSERT INTO LaunchpadDatabaseRevision VALUES (2208, 99, 0);
