SET client_min_messages TO error;

/* Table not needed - false alarm */
DROP TABLE scrapedproject;

/* Bug in foreign key for Malone */
ALTER TABLE productbugassignment DROP CONSTRAINT "$2";
ALTER TABLE productbugassignment ADD FOREIGN KEY (product) REFERENCES Product;

