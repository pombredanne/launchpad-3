SET client_min_messages=ERROR;

-- Add the new column for external_id
ALTER TABLE Entitlement
    ADD COLUMN dirty BOOLEAN NOT NULL DEFAULT true;

INSERT INTO LaunchpadDatabaseRevision VALUES(87, 99, 0);
