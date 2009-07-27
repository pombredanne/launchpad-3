-- Copyright 2009 Canonical Ltd.  This software is licensed under the
-- GNU Affero General Public License version 3 (see the file LICENSE).

SET client_min_messages=ERROR;

-- Since we are modifying branch, we need to replace the
-- 'special' view.  This will die shortly, thumper promises.
DROP VIEW BranchWithSortKeys;

-- Remove pull_disabled from Branch, it's no longer used.
ALTER TABLE Branch
DROP COLUMN pull_disabled;

CREATE OR REPLACE VIEW BranchWithSortKeys AS
    SELECT Branch.*,
           Product.name AS product_name,
           Author.displayname AS author_name,
           Owner.displayname AS owner_name
    FROM Branch
    INNER JOIN Person AS Owner ON Branch.owner = Owner.id
    LEFT OUTER JOIN Product ON Branch.product = Product.id
    LEFT OUTER JOIN Person as Author ON Branch.author = Author.id;

INSERT INTO LaunchpadDatabaseRevision VALUES (2109, 2, 0);
