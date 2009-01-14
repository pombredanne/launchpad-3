SET client_min_messages=ERROR;

ALTER TABLE Product
    ADD COLUMN registrant int REFERENCES Person;

-- Unfortunately we can't recreate who originally registered the
-- product, so defaulting to the owner will have to
-- do.
UPDATE Product
SET registrant = owner;

ALTER TABLE Product
  ALTER COLUMN registrant SET NOT NULL;

-- Create an index.
CREATE INDEX product__registrant__idx
  ON Product(registrant);

ALTER TABLE Project
    ADD COLUMN registrant int REFERENCES Person;

-- Unfortunately we can't recreate who originally registered the
-- project, so defaulting to the owner will have to
-- do.
UPDATE Project
SET registrant = owner;

ALTER TABLE Project
  ALTER COLUMN registrant SET NOT NULL;

-- Create an index.
CREATE INDEX project__registrant__idx
  ON Project(registrant);

INSERT INTO LaunchpadDatabaseRevision VALUES (121, 73, 0);
