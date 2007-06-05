SET client_min_messages=ERROR;

ALTER TABLE Person ADD COLUMN registrant integer;
ALTER TABLE Person ADD CONSTRAINT person_registrant_fk
    FOREIGN KEY (registrant) REFERENCES Person(id);

INSERT INTO LaunchpadDatabaseRevision VALUES (67, 28, 0);
