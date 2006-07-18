SET client_min_messages=ERROR;

/* We want to add an explicit "driver" person to Distribution,
   DistroRelease, Product and ProductSeries. These people will have
   permission to approve specs and bugs proposed for implementation or
   fixing in the series/release.
*/

ALTER TABLE Distribution ADD COLUMN driver integer;
ALTER TABLE Distribution ADD CONSTRAINT distribution_driver_fk
  FOREIGN KEY (driver) REFERENCES Person(id);


ALTER TABLE Product ADD COLUMN driver integer;
ALTER TABLE Product ADD CONSTRAINT product_driver_fk
  FOREIGN KEY (driver) REFERENCES Person(id);


ALTER TABLE DistroRelease ADD COLUMN driver integer;
ALTER TABLE DistroRelease ADD CONSTRAINT distrorelease_driver_fk
  FOREIGN KEY (driver) REFERENCES Person(id);


ALTER TABLE ProductSeries ADD COLUMN driver integer;
ALTER TABLE ProductSeries ADD CONSTRAINT productseries_driver_fk
  FOREIGN KEY (driver) REFERENCES Person(id);


ALTER TABLE Project ADD COLUMN driver integer;
ALTER TABLE Project ADD CONSTRAINT project_driver_fk
  FOREIGN KEY (driver) REFERENCES Person(id);


  -- we also want an owner on the productseries table. we removed that
  -- some time ago but actually, we want that on every table!

ALTER TABLE ProductSeries ADD COLUMN owner integer;
UPDATE ProductSeries SET owner = Product.owner
    FROM Product WHERE ProductSeries.product=Product.id;
ALTER TABLE ProductSeries ADD CONSTRAINT productseries_owner_fk
  FOREIGN KEY (owner) REFERENCES Person(id);
ALTER TABLE ProductSeries ALTER COLUMN owner SET NOT NULL;

  -- and finally we will get rid of displayname in favour of just
  -- using the name everywhere

ALTER TABLE ProductSeries DROP COLUMN displayname;

  -- in the ProductRelease, we have a manufactured .title, but we
  -- want to be able to access the codename directly

ALTER TABLE ProductRelease RENAME COLUMN title TO codename;

  -- while we are here, lets make the product description optional

ALTER TABLE Product ALTER COLUMN description DROP NOT NULL;

/* Informational Specs
   Some specifications are never implemented, they are just "informational"
   and describe how part of the system is supposed to be used. We currently
   flag those with a status value, but it is really a separate property of
   the spec. So let's go to that model.

   The dbschema value for SpecificationStatus.Informational (was) 55.

*/

ALTER TABLE Specification ADD COLUMN informational boolean;
UPDATE Specification SET informational=FALSE;
UPDATE Specification SET informational=TRUE, status=10, delivery=90
    WHERE status=55;
ALTER TABLE Specification ALTER COLUMN informational SET DEFAULT False;
ALTER TABLE Specification ALTER COLUMN informational SET NOT NULL;


INSERT INTO LaunchpadDatabaseRevision VALUES (40, 48, 0);

