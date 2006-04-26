SET client_min_messages=ERROR;

CREATE UNIQUE INDEX branch_name_owner_product_key
    ON Branch (name, owner, COALESCE(product, -1));

CREATE INDEX specification_datecreated_idx ON Specification(datecreated);

INSERT INTO LaunchpadDatabaseRevision VALUES (40, 49, 1);
