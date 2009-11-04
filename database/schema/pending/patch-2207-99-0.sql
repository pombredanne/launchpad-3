SET client_min_messages=ERROR;

ALTER TABLE Product
    ADD COLUMN translation_focus int,
    ADD CONSTRAINT product__productseries__fk
        FOREIGN KEY (translation_focus) REFERENCES productseries(id);

INSERT INTO LaunchpadDatabaseRevision VALUES (2207, 99, 0);
