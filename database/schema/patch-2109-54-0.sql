SET client_min_messages=ERROR;

ALTER TABLE ProductSeries
ADD COLUMN translations_branch INTEGER REFERENCES Branch(id);

CREATE INDEX productseries__translations_branch__idx
ON ProductSeries(translations_branch);

INSERT INTO LaunchpadDatabaseRevision VALUES (2109, 54, 0);
