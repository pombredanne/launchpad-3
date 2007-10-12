SET client_min_messages=ERROR;

CREATE OR REPLACE VIEW BranchAndProduct AS
    SELECT Branch.*,
           Product.name AS product_name,
           Author.displayname AS author_name,
           Owner.displayname AS owner_name
    FROM Branch
    LEFT OUTER JOIN Product ON Branch.product = Product.id
    LEFT OUTER JOIN Person as Author ON Branch.author = Author.id
    LEFT OUTER JOIN Product as Owner ON Branch.owner = Owner.id;

INSERT INTO LaunchpadDatabaseRevision VALUES (87, 88, 0);
