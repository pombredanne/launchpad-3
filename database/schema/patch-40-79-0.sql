SET client_min_messages=ERROR;

/* We want to add an explicit "driver" person to Distribution,
   DistroRelease, Product and ProductSeries. These people will have
   permission to approve specs and bugs proposed for implementation or
   fixing in the series/release.
*/

ALTER TABLE Distribution ADD COLUMN driver integer;
ALTER TABLE Distribution ADD CONSTRAINT distribution_driver_fk
  FOREIGN KEY (driver) REFERENCES Person(id);

COMMENT ON COLUMN Distribution.driver IS 'The team or person responsible for approving goals for each release in the distribution. This should usually be a very small team because the Distribution driver can approve items for backporting to past releases as well as the current release under development. Each distrorelease has its own driver too, so you can have the small superset in the Distribution driver, and then specific teams per distrorelease for backporting, for example, or for the current release management team on the current development focus release.';

ALTER TABLE Product ADD COLUMN driver integer;
ALTER TABLE Product ADD CONSTRAINT product_driver_fk
  FOREIGN KEY (driver) REFERENCES Person(id);

COMMENT ON COLUMN Product.driver IS 'This is a driver for the overall product. This driver will be able to approve nominations of bugs and specs to any series in the product, including backporting to old stable series. You want the smallest group of "overall drivers" here, because you can add specific drivers to each series individually.';

ALTER TABLE DistroRelease ADD COLUMN driver integer;
ALTER TABLE DistroRelease ADD CONSTRAINT distrorelease_driver_fk
  FOREIGN KEY (driver) REFERENCES Person(id);

COMMENT ON COLUMN DistroRelease.driver IS 'This is a person or team who can act as a driver for this specific release - note that the distribution drivers can also set goals for any release.';

ALTER TABLE ProductSeries ADD COLUMN driver integer;
ALTER TABLE ProductSeries ADD CONSTRAINT productseries_driver_fk
  FOREIGN KEY (driver) REFERENCES Person(id);

COMMENT ON COLUMN ProductSeries.driver IS 'This is a person or team who can approve spes and bugs for implementation or fixing in this specific series. Note that the product drivers and project drivers can also do this for any series in the product or project, so use this only for the specific team responsible for this specific series.';

ALTER TABLE Project ADD COLUMN driver integer;
ALTER TABLE Project ADD CONSTRAINT project_driver_fk
  FOREIGN KEY (driver) REFERENCES Person(id);

COMMENT ON COLUMN Project.driver IS 'This person or team has the ability to approve specs as goals for any series in any product in the project. Similarly, this person or team can approve bugs as targets for fixing in any series, or backporting of fixes to any series.';

  -- we also want an owner on the productseries table. we removed that
  -- some time ago but actually, we want that on every table!

ALTER TABLE ProductSeries ADD COLUMN owner integer;
UPDATE ProductSeries SET owner = (
  SELECT id FROM Person WHERE name='sabdfl');
ALTER TABLE ProductSeries ADD CONSTRAINT productseries_owner_fk
  FOREIGN KEY (owner) REFERENCES Person(id);
ALTER TABLE ProductSeries ALTER COLUMN owner SET NOT NULL;

  -- and finally we will get rid of displayname in favour of just
  -- using the name everywhere

ALTER TABLE ProductSeries DROP COLUMN displayname;

  -- in the ProductRelease, we have a manufactured .title, but we
  -- want to be able to access the codename directly

ALTER TABLE ProductRelease RENAME COLUMN title TO codename;

INSERT INTO LaunchpadDatabaseRevision VALUES (40, 79, 0);

