SET client_min_messages=ERROR;

/* Make SourceSource reference productseries instead of product */

-- Add the new column

ALTER TABLE SourceSource ADD COLUMN productseries integer
    CONSTRAINT sourcesource_productseries_fk REFERENCES ProductSeries;

-- Migrate data. First create a productseries for every product referenced
-- by SourceSource that doesn't already have one. We choose default
-- names that should be applicable to the majority of the new product
-- series. Unsuitable data needs to be cleaned up after this patch is
-- applied.
INSERT INTO ProductSeries (product, name, displayname, shortdesc)
    SELECT DISTINCT
        Product.id,
        'main' AS name, -- not MAIN, since names must be lower case
        'Main release' AS displayname,
        'The standard release' AS shortdesc
    FROM SourceSource
        JOIN Product ON SourceSource.product = Product.id
        LEFT OUTER JOIN ProductSeries ON Product.id = ProductSeries.product
    WHERE ProductSeries.id IS NULL;

-- Next update SourceSource rows that reference a Product to reference
-- the corresponding productseries. If there are two or more ProductSeries,
-- we select the most recently added one.
UPDATE SourceSource SET productseries = (
    SELECT MAX(ProductSeries.id)
    FROM Product JOIN ProductSeries ON Product.id = ProductSeries.product
    WHERE SourceSource.product = Product.id
    GROUP BY Product.id
    );

-- Drop the unwanted Product column
ALTER TABLE SourceSource DROP COLUMN product;

-- Tidy up some unnamed constraints while we are here
ALTER TABLE SourceSource DROP CONSTRAINT "$6";
ALTER TABLE SourceSource DROP CONSTRAINT "$5";
ALTER TABLE SourceSource DROP CONSTRAINT "$3";
ALTER TABLE SourceSource DROP CONSTRAINT "$2";
ALTER TABLE SourceSource ADD CONSTRAINT sourcesource_owner_fk
    FOREIGN KEY (owner) REFERENCES Person;
ALTER TABLE SourceSource ADD CONSTRAINT sourcesource_branch_fk
    FOREIGN KEY (branch) REFERENCES Branch;
ALTER TABLE SourceSource ADD CONSTRAINT sourcesource_releaseparentbranch_fk
    FOREIGN KEY (releaseparentbranch) REFERENCES Branch;
ALTER TABLE SourceSource ADD CONSTRAINT sourcesource_cvstarfile_fk
    FOREIGN KEY (cvstarfile) REFERENCES LibraryFileAlias;

INSERT INTO LaunchpadDatabaseRevision VALUES (14, 99, 0);

