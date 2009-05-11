SET client_min_messages=ERROR;

ALTER TABLE ProductSeries
ADD COLUMN translations_branch INTEGER REFERENCES Branch(id);

-- INSERT INTO LaunchpadDatabaseRevision VALUES (2109, 99, 0);
