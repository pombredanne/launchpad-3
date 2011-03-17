-- Copyright 2011 Canonical Ltd.  This software is licensed under the
-- GNU Affero General Public License version 3 (see the file LICENSE).

SET client_min_messages=ERROR;

-- Convert DistroSeriesDifference source_version, parent_source_version,
-- and base_version types to debversion.

-- Change types.
ALTER TABLE DistroSeriesDifference ALTER COLUMN source_version TYPE debversion;
ALTER TABLE DistroSeriesDifference ALTER COLUMN parent_source_version TYPE debversion;
ALTER TABLE DistroSeriesDifference ALTER COLUMN base_version TYPE debversion;

-- Create indexes.
CREATE INDEX SourcePackageRelease__source_version__idx
    ON DistroSeriesDifference(source_version);
CREATE INDEX BinaryPackageRelease__parent_source_version__idx
    ON DistroSeriesDifference(parent_source_version);
CREATE INDEX BinaryPackageRelease__base_version__idx
    ON DistroSeriesDifference(base_version);


INSERT INTO LaunchpadDatabaseRevision VALUES (2208, 99, 0);
