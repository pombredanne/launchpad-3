SET client_min_messages=ERROR;

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
        Product.id, Product.name, Product.displayname, Product.shortdesc,
        ProductRelease.id
    FROM
        POTemplate
        JOIN ProductRelease ON POTemplate.productrelease = ProductRelease.id
        JOIN Product ON ProductRelease.product = Product.id
    WHERE
        POTemplate.productrelease IS NOT NULL
        AND ProductRelease.productseries IS NULL;

INSERT INTO ProductSeries (id, product, name, displayname, shortdesc)
    SELECT id, product, name, displayname, shortdesc FROM TmpProductSeries;

UPDATE ProductRelease SET productseries=TmpProductSeries.id
    FROM TmpProductSeries
    WHERE ProductRelease.id = TmpProductSeries.productrelease;

DROP TABLE TmpProductSeries;

INSERT INTO LaunchpadDatabaseRevision VALUES (11, 13, 0);

