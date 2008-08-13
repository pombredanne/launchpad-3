SET client_min_messages=ERROR;

-- Refer to the Message table directly instead of through the Message-ID
ALTER TABLE messageapproval
    ADD COLUMN message integer NOT NULL;

-- Keep the message_id field for now, but allow it to be NULL.  We'll do a
-- data migration operation and drop the column later.
ALTER TABLE messageapproval
    ALTER COLUMN message_id DROP NOT NULL;

ALTER TABLE ONLY messageapproval
    ADD CONSTRAINT messageapproval_message_fkey
    FOREIGN KEY (message) REFERENCES message(id);

INSERT INTO LaunchpadDatabaseRevision VALUES (121, 99, 0);
