SET client_min_messages=ERROR;

/* Don't allow filenames to contain a / character as the Librarian cannot
serve them, and if it did could be used for (probably lame) social
engineering attacks.
*/

ALTER TABLE ProductSeries
  RENAME COLUMN branch TO import_branch;
ALTER TABLE ProductSeries
  ADD COLUMN user_branch integer;
ALTER TABLE ProductSeries
  ADD CONSTRAINT productseries_user_branch_key
  FOREIGN KEY (user_branch) REFERENCES Branch(id);

INSERT INTO LaunchpadDatabaseRevision VALUES (67, 95, 0);

