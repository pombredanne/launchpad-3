SET client_min_messages=ERROR;

/* Make sure all products have at least one series */
INSERT INTO ProductSeries (product, owner, name, summary)
  SELECT
    Product.id,
    Product.owner,
    'trunk' AS name,
    'The "trunk" series represents the primary line of development rather than a stable release branch. This is sometimes also called MAIN or HEAD.' AS summary
  FROM Product LEFT JOIN ProductSeries ON Product.id = ProductSeries.product
  GROUP BY Product.id, Product.owner
  HAVING COUNT(ProductSeries.id) = 0;


/* Add development_focus column.
 *
 * This column should be NOT NULL, but when creating a product, we
 * won't know what value to use til the first product series has been
 * created.  A deferred constraint would work, but Postgres only
 * supports deferred foreign key constraints.
 */

ALTER TABLE Product
  ADD COLUMN development_focus integer;
ALTER TABLE Product
  ADD CONSTRAINT product__development_focus__fk
  FOREIGN KEY (development_focus) REFERENCES ProductSeries(id);


/* Populate the development_focus for existing products:
 *  1. If the product has a "trunk" series, we pick that.
 *  2. Otherwise, if it has a "main" series, we pick that.
 *  3. Otherwise, we pick the series with the lowest ID.
 */

UPDATE Product SET development_focus = ProductSeries.id
  FROM ProductSeries
  WHERE
    Product.id = ProductSeries.product AND
    ProductSeries.name = 'trunk' AND
    Product.development_focus IS NULL;

UPDATE Product SET development_focus = ProductSeries.id
  FROM ProductSeries
  WHERE
    Product.id = ProductSeries.product AND
    ProductSeries.name = 'main' AND
    Product.development_focus IS NULL;

UPDATE Product SET development_focus = tmp.id
  FROM (
    SELECT product, min(id) as id from ProductSeries
      GROUP BY product) AS tmp
  WHERE Product.id = tmp.product AND Product.development_focus IS NULL;

INSERT INTO LaunchpadDatabaseRevision VALUES (67, 20, 0);
