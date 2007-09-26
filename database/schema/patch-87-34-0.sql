SET client_min_messages=ERROR;

ALTER TABLE CodeImport
ADD COLUMN owner integer REFERENCES Person(id),
ADD COLUMN assignee integer REFERENCES Person(id),
ADD COLUMN update_interval interval;

UPDATE CodeImport SET owner=registrant;
ALTER TABLE CodeImport ALTER owner SET NOT NULL;

-- Keep people merge happy
CREATE INDEX codeimport__owner__idx ON CodeImport(owner);
CREATE INDEX codeimport__assignee__idx ON CodeImport(assignee);


/* Turn the CodeImportMachine.online bool into a CodeImportMachine.state enum,
with three states OFFLINE (10), ONLINE (20) and QUIESCING (30).

Also implement data migration, this is not terribly useful since we should not
have any data to migrate yet either in the sampledata or in production. But
it would be the correct thing to do if we had some. */

ALTER TABLE CodeImportMachine ADD COLUMN state integer;
UPDATE CodeImportMachine SET state=(
    CASE WHEN online=FALSE THEN 10 -- OFFLINE
         WHEN online=TRUE THEN 20  -- ONLINE
    END);
ALTER TABLE CodeImportMachine
ADD COLUMN heartbeat TIMESTAMP WITHOUT TIME ZONE,
ALTER COLUMN state SET NOT NULL,
ALTER COLUMN state SET DEFAULT 10, -- OFFLINE
DROP COLUMN online;

INSERT INTO LaunchpadDatabaseRevision VALUES (87, 34, 0);
