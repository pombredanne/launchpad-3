SET client_min_messages=ERROR;

ALTER TABLE Branch
  ADD COLUMN registrant int REFERENCES Person;

-- Unfortunately we can't recreate who originally registered the
-- branch, but the number of branches that have been reassigned
-- is relatively small, so defaulting to the owner will have to
-- do.
UPDATE Branch
SET registrant = owner;

ALTER TABLE Branch
  ALTER COLUMN registrant SET NOT NULL;

-- Need indexes for people merge
CREATE INDEX branch__registrant__idx
  ON Branch(registrant);

-- Since we are modifying branch, we need to replace the
-- 'special' view.  This will die shortly, I promise.
DROP VIEW BranchWithSortKeys;
CREATE OR REPLACE VIEW BranchWithSortKeys AS
    SELECT Branch.*,
           Product.name AS product_name,
           Author.displayname AS author_name,
           Owner.displayname AS owner_name
    FROM Branch
    INNER JOIN Person AS Owner ON Branch.owner = Owner.id
    LEFT OUTER JOIN Product ON Branch.product = Product.id
    LEFT OUTER JOIN Person as Author ON Branch.author = Author.id;

INSERT INTO LaunchpadDatabaseRevision VALUES (121, 1, 0);
