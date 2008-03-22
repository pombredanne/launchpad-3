SET client_min_messages=ERROR;

ALTER TABLE Product
    ADD COLUMN official_codehosting BOOLEAN NOT NULL DEFAULT FALSE;

/* Set official_codehosting value to True if the development focus series of
   the product has a hosted branch specified */
UPDATE Product
SET official_codehosting = TRUE
WHERE id IN (
    SELECT product.id FROM product, productseries, branch
    WHERE product.development_focus = productseries.id
    AND productseries.user_branch = branch.id
    AND branch.branch_type = 1
);

INSERT INTO LaunchpadDatabaseRevision VALUES (121, 14, 0);
