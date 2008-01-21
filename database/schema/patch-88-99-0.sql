SET client_min_messages=ERROR;

ALTER TABLE Product
    ADD COLUMN official_codehosting BOOLEAN;
/* Set official_codhosting value to True if the development focus series of
   the product has a user branch specified */
UPDATE Product
SET official_codehosting = TRUE
WHERE id IN (
    SELECT product.id FROM product, productseries
    WHERE product.development_focus = productseries.id
    AND productseries.user_branch IS NOT NULL
);

UPDATE Product
SET official_codehosting = FALSE
WHERE official_codehosting IS NULL;

ALTER TABLE Product ALTER COLUMN official_codehosting
    SET DEFAULT FALSE;

ALTER TABLE Product ALTER COLUMN official_codehosting
    SET NOT NULL;

INSERT INTO LaunchpadDatabaseRevision VALUES (88, 99, 0);
