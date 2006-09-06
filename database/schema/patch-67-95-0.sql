SET client_min_messages=ERROR;

/*
 * Rename ProductSeries.branch to import_branch, and add a new user_branch
 * field.
 */

ALTER TABLE ProductSeries
  RENAME COLUMN branch TO import_branch;
ALTER TABLE ProductSeries
  ADD COLUMN user_branch integer;

/* Split the productseries_branch_fk constraint */
ALTER TABLE ProductSeries
  ADD CONSTRAINT productseries_import_branch_fk
  FOREIGN KEY (import_branch) REFERENCES Branch(id);
ALTER TABLE ProductSeries
  ADD CONSTRAINT productseries_user_branch_fk
  FOREIGN KEY (user_branch) REFERENCES Branch(id);
ALTER TABLE ProductSeries
  DROP CONSTRAINT productseries_branch_fk;

/* Split the productseries_branch_key constraint */
ALTER TABLE ProductSeries
  ADD CONSTRAINT productseries_import_branch_key
  UNIQUE (import_branch);
ALTER TABLE ProductSeries
  ADD CONSTRAINT productseries_user_branch_key
  UNIQUE (user_branch);
ALTER TABLE ProductSeries
  DROP CONSTRAINT productseries_branch_key;

INSERT INTO LaunchpadDatabaseRevision VALUES (67, 95, 0);

