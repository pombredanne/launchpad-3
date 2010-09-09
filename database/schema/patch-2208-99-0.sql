SET client_min_messages=ERROR;

-- Allow for package diffs against both derived and parent versions.
ALTER TABLE DistroSeriesDifference ADD COLUMN parent_package_diff integer CONSTRAINT distroseriesdifference__parent_package_diff__fk REFERENCES packagediff;
CREATE INDEX distroseriesdifference__parent_package_diff__idx ON distroseriesdifference(parent_package_diff);

-- Add columns for source_version and parent_source_version
ALTER TABLE DistroSeriesDifference ADD COLUMN source_version text;
ALTER TABLE DistroSeriesDifference ADD COLUMN parent_source_version text;

-- Add a unique constraint/index for the source_package_name/derived series combo.
ALTER TABLE DistroSeriesDifference ADD CONSTRAINT distroseriesdifference_source_package_name__derived_series__uni UNIQUE (derived_series, source_package_name);

INSERT INTO LaunchpadDatabaseRevision VALUES (2208, 99, 0);
