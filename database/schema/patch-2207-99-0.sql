-- Copyright 2009 Canonical Ltd.  This software is licensed under the
-- GNU Affero General Public License version 3 (see the file LICENSE).

ALTER TABLE BinaryPackageRelease
    ADD COLUMN ddeb_package integer REFERENCES BinaryPackageRelease;

CREATE UNIQUE INDEX binarypackagerelease__ddeb_package__key
    ON BinaryPackageRelease(ddeb_package);

INSERT INTO LaunchpadDatabaseRevision VALUES (2207, 99, 0);
