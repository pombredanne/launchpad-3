set client_min_messages=ERROR;

-- Needed to speed up Gina
create index binarypackage_version_idx on binarypackage(version);

INSERT INTO LaunchpadDatabaseRevision VALUES (17, 43, 0);

