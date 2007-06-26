SET client_min_messages=ERROR;

-- Add the new column for external_id
ALTER TABLE Entitlement
    ADD COLUMN external_id TEXT;

INSERT INTO LaunchpadDatabaseRevision VALUES(87, 99, 0);
