-- Copyright 2017 Canonical Ltd.  This software is licensed under the
-- GNU Affero General Public License version 3 (see the file LICENSE).

SET client_min_messages=ERROR;

ALTER TABLE SourcePackageRelease ADD COLUMN buildinfo integer REFERENCES libraryfilealias;
ALTER TABLE BinaryPackageBuild ADD COLUMN buildinfo integer REFERENCES libraryfilealias;

INSERT INTO LaunchpadDatabaseRevision VALUES (2209, 82, 0);
