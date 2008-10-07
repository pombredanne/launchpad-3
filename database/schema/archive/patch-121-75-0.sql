SET client_min_messages=ERROR;

ALTER TABLE Revision
    ADD COLUMN karma_allocated boolean DEFAULT FALSE;
CREATE INDEX revision__karma_allocated__idx ON Revision(karma_allocated)
    WHERE karma_allocated IS FALSE;

INSERT INTO LaunchpadDatabaseRevision VALUES (121, 75, 0);
