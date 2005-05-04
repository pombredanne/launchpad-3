SET client_min_messages=ERROR;

/*
 Migrate data. These statements create a new ProductSeries for each
 ProductRelease that does not already have one, with the name and
 description copied from the Product.
 */
CREATE TEMPORARY TABLE TmpProductSeries (
        id integer DEFAULT nextval('productseries_id_seq'),
        product integer,
        name text,
        displayname text,
        shortdesc text,
        productrelease integer
        );

INSERT INTO TmpProductSeries
    (product, name, displayname, shortdesc, productrelease)
    SELECT DISTINCT
        Product.id,
        'main',
        'MAIN',
        'The primary "trunk" of development for this product. This series
was automatically created and represents the idea of a primary trunk
of software development without "stable branches". For most
products, releases in this series will be "milestone" or "test"
releases, and there should be other series for the stable releases
of the product.',
        ProductRelease.id
    FROM
        ProductRelease
        JOIN Product ON ProductRelease.product = Product.id
    WHERE
        ProductRelease.productseries IS NULL;

INSERT INTO ProductSeries (id, product, name, displayname, shortdesc)
    SELECT id, product, name, displayname, shortdesc FROM TmpProductSeries;

UPDATE ProductRelease SET productseries=TmpProductSeries.id
    FROM TmpProductSeries
    WHERE ProductRelease.id = TmpProductSeries.productrelease;

DROP TABLE TmpProductSeries;

/* Alter database schema. ProductRelease is not linked to the Product
   via the ProductSeries table
 */
ALTER TABLE ProductRelease ALTER COLUMN ProductSeries SET NOT NULL;
ALTER TABLE ProductRelease DROP COLUMN product;


INSERT INTO LaunchpadDatabaseRevision VALUES (14,1,0);

