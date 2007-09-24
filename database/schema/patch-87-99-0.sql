SET client_min_messages=ERROR;

ALTER TABLE product
    ADD COLUMN license integer;

INSERT INTO LaunchpadDatabaseRevision VALUES (87, 99, 0);
