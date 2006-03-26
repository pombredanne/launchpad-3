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

INSERT INTO LaunchpadDatabaseRevision VALUES (40, 79, 0);

