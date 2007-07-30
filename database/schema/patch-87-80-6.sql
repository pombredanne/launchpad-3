SET client_min_messages=ERROR;


ALTER TABLE CodeImport ADD COLUMN assignee integer REFERENCES Person(id);
ALTER TABLE CodeImport ADD COLUMN update_interval interval;

ALTER TABLE CodeImportMachine ADD COLUMN
    heartbeat TIMESTAMP WITHOUT TIME ZONE;

ALTER TABLE CodeImportMachine ADD COLUMN state integer;

/* This is not terribly useful since we should not have any row in this table
yet either in the sampledata or in production. But it would be the correct
thing to do should we have data to migrate. */
UPDATE CodeImportMachine SET state=(
    CASE WHEN online=FALSE THEN 10
         WHEN online=TRUE THEN 20
    END);

ALTER TABLE CodeImportMachine ALTER state SET NOT NULL;
ALTER TABLE CodeImportMachine DROP COLUMN online;

INSERT INTO LaunchpadDatabaseRevision VALUES (87, 80, 6);

