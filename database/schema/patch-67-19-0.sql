SET client_min_messages=ERROR;

ALTER TABLE Person ADD COLUMN creation_rationale integer;
ALTER TABLE Person ADD COLUMN creation_comment text;

UPDATE Person SET creation_rationale = 1 
    WHERE id NOT IN (SELECT id FROM ValidPersonOrTeamCache);

-- XXX: These ones may not be needed before DirectPersonCreation
--ALTER TABLE Person ADD COLUMN registrant integer;
--ALTER TABLE Person ADD CONSTRAINT person_registrant_fk
--    FOREIGN KEY (registrant) REFERENCES Person(id);

INSERT INTO LaunchpadDatabaseRevision VALUES (67, 19, 0);

