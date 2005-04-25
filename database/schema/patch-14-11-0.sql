
SET client_min_messages=ERROR;

/* Packaging

   The packaging table needs to point at a product series rather than a
   product. We add productseries to packaging, then try to populate it
   before removing the old product link.
*/

ALTER TABLE Packaging ADD COLUMN productseries integer;
ALTER TABLE Packaging ADD CONSTRAINT packaging_productseries_fk
    FOREIGN KEY (productseries) REFERENCES ProductSeries(id);

-- make sure we have a ProductSeries for every product that has packaging
-- details
INSERT INTO ProductSeries (product, name, displayname, shortdesc)
    SELECT DISTINCT
        Product.id,
        'main' AS name, -- not MAIN, since names must be lower case
        'MAIN' AS displayname,
        'The primary "trunk" of development for this product. This series
was automatically created and represents the idea of a primary trunk
of software development without "stable branches". For most
products, releases in this series will be "milestone" or "test"
releases, and there should be other series for the stable releases
of the product.' AS shortdesc
    FROM Packaging
        JOIN Product ON Packaging.product = Product.id
        LEFT OUTER JOIN ProductSeries ON Product.id = ProductSeries.product
    WHERE ProductSeries.id IS NULL;

-- add the productseries data to the packaging records, assuming whatever
-- packaging we have points at the latest series of a product
UPDATE Packaging SET productseries = (
    SELECT MAX(ProductSeries.id)
    FROM Product JOIN ProductSeries ON Product.id = ProductSeries.product
    WHERE Packaging.product = Product.id
    GROUP BY Product.id);

-- there should be a productseries in every Packaging row now
ALTER TABLE Packaging ALTER COLUMN productseries SET NOT NULL;

-- now we can drop the product column from the Packaging table
ALTER TABLE Packaging DROP COLUMN product;

-- we certainly only want one type of packaging for any given
-- productseries, distrorelease and sourcepackagename
ALTER TABLE Packaging ADD CONSTRAINT packaging_uniqueness
    UNIQUE( distrorelease, sourcepackagename, productseries );

INSERT INTO LaunchpadDatabaseRevision VALUES (14, 11, 0);
