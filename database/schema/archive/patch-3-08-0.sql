SET client_min_messages TO error;


/*
  - Give each Series a shortdesc as well.
  - Allow a ProductReleast to be in a Series
*/

ALTER TABLE ProductSeries ADD COLUMN shortdesc TEXT;
UPDATE ProductSeries SET shortdesc=displayname;
ALTER TABLE ProductSeries ALTER COLUMN shortdesc SET NOT NULL;

/*
  - Give each ProductRelease a shortdesc as well.
*/

ALTER TABLE ProductRelease ADD COLUMN shortdesc TEXT;

ALTER TABLE ProductRelease ADD COLUMN productseries INT 
    REFERENCES ProductSeries;

