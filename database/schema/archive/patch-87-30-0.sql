SET client_min_messages=ERROR;

-- Add the new column for external_id
ALTER TABLE Entitlement
    ADD COLUMN is_dirty BOOLEAN NOT NULL DEFAULT TRUE;

INSERT INTO LaunchpadDatabaseRevision VALUES(87, 30, 0);
