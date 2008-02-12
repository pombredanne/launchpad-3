SET client_min_messages=ERROR;

-- Rename mirror_request_time to next_mirror_time
ALTER TABLE branch RENAME COLUMN mirror_request_time TO next_mirror_time;

CREATE INDEX branch__next_mirror_time__idx ON Branch(next_mirror_time)
WHERE next_mirror_time IS NOT NULL;

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

INSERT INTO LaunchpadDatabaseRevision VALUES (88, 32, 0);
