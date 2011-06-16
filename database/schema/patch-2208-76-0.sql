-- Copyright 2011 Canonical Ltd.  This software is licensed under the
-- GNU Affero General Public License version 3 (see the file LICENSE).

SET client_min_messages=ERROR;

CREATE TABLE BinaryPackagePaths (
    id serial PRIMARY KEY,
    path text UNIQUE NOT NULL
);

CREATE TABLE BinaryPackageReleaseContents (
    binarypackagerelease integer NOT NULL REFERENCES BinaryPackageRelease,
    binarypackagepath integer NOT NULL REFERENCES BinaryPackagePaths,
    PRIMARY KEY (binarypackagerelease, binarypackagepath)
);

INSERT INTO LaunchpadDatabaseRevision VALUES (2208, 76, 0);
