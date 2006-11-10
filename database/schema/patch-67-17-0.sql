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
  ADD CONSTRAINT productseries__import_branch__fk
  FOREIGN KEY (import_branch) REFERENCES Branch(id);
ALTER TABLE ProductSeries
  ADD CONSTRAINT productseries__user_branch__fk
  FOREIGN KEY (user_branch) REFERENCES Branch(id);
ALTER TABLE ProductSeries
  DROP CONSTRAINT productseries_branch_fk;

/*
 * Rename the productseries_branch_key constraint.
 * The uniqueness constraint is only required for importd's work, so
 * we don't have an equivalent user_branch one.
 */
ALTER TABLE ProductSeries
  ADD CONSTRAINT productseries__import_branch__key
  UNIQUE (import_branch);
ALTER TABLE ProductSeries
  DROP CONSTRAINT productseries_branch_key;

INSERT INTO LaunchpadDatabaseRevision VALUES (67, 17, 0);

