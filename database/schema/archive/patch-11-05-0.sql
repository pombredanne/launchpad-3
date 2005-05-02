SET client_min_messages=ERROR;

ALTER TABLE SourceSource ADD CONSTRAINT sourcesource_name_key UNIQUE (name);

INSERT INTO LaunchpadDatabaseRevision VALUES (11,5,0);

