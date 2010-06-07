SET client_min_messages=ERROR;

-- Bug #49717
ALTER TABLE SourcePackageRelease ALTER component SET NOT NULL;

INSERT INTO LaunchpadDatabaseRevision VALUES (2207, 62, 0);
