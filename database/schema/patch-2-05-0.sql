/* Temporary table for holding sample data imported from Freshmeat/Sourceforge.
    Data in this table will be validated and moved into the Product table.
 */

/* TODO:
    How does the scraper know if it has already scraped a particular
    entry? I think it will either need to check if the homepageurl
    already exists (so that will need to be UNIQUE), or we need an
    external id or something (eg. sourceforge project number etc.,
    with mangling to make sure they don't clash)

*/

SET client_min_messages TO error;

CREATE TABLE ScrapedProject (
    id serial PRIMARY KEY,
    description text NOT NULL,
    homepageurl text,
    screenshotsurl text,
    wikiurl text,
    listurl text,
    programminglang text
    );

SET client_min_messages TO error;

/* Extra columns on the GPGKey table for Soyuz */

ALTER TABLE GPGKey ADD COLUMN algorithm int;
ALTER TABLE GPGKey ADD COLUMN keysize int;
ALTER TABLE GPGKey ALTER COLUMN algorithm SET NOT NULL;
ALTER TABLE GPGKey ALTER COLUMN keysize SET NOT NULL;

