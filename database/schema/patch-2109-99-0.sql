SET client_min_messages=ERROR;

ALTER TABLE ProductSeries
  ADD COLUMN branch INT REFERENCES Branch;

UPDATE ProductSeries
  SET branch=COALESCE (user_branch, import_branch);

ALTER TABLE ProductSeries
  DROP COLUMN user_branch,
  DROP COLUMN import_branch;

CREATE INDEX productseries__branch__idx ON ProductSeries(branch)
  WHERE branch IS NOT NULL;

INSERT INTO LaunchpadDatabaseRevision VALUES (2109, 99, 0);

