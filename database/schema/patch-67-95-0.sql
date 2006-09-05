SET client_min_messages=ERROR;

/*
 * Rename ProductSeries.branch to import_branch, and add a new user_branch
 * field.
 */

ALTER TABLE ProductSeries
  RENAME COLUMN branch TO import_branch;
ALTER TABLE ProductSeries
  ADD COLUMN user_branch integer;
ALTER TABLE ProductSeries
  ADD CONSTRAINT productseries_user_branch_key
  FOREIGN KEY (user_branch) REFERENCES Branch(id);

INSERT INTO LaunchpadDatabaseRevision VALUES (67, 95, 0);

