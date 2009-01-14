SET client_min_messages=ERROR;

-- Refer to the Message table directly instead of through the Message-ID
ALTER TABLE messageapproval
    ADD COLUMN message integer;

-- Migrate the single ambiguous case
UPDATE MessageApproval
SET message = 2465682
WHERE message_id
    = '<dcf99d5d0808101018o3bc428edmf76a9090a6d6f698@mail.gmail.com>';
    
-- And migrate the rest
UPDATE MessageApproval
SET message=(
    SELECT Message.id FROM Message
    WHERE rfc822msgid=MessageApproval.message_id
    )
WHERE message IS NULL;

ALTER TABLE messageapproval
    DROP COLUMN message_id,
    ALTER COLUMN message SET NOT NULL,
    ADD CONSTRAINT messageapproval_message_fkey
        FOREIGN KEY (message) REFERENCES message(id);

CREATE INDEX messageapproval__message__idx ON MessageApproval(message);

INSERT INTO LaunchpadDatabaseRevision VALUES (121, 80, 0);
