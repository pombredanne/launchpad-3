SET client_min_messages=ERROR;

UPDATE bug SET description=(
    SELECT messagechunk.content
    FROM bugmessage,message,messagechunk
    WHERE
        bugmessage.bug=bug.id
        AND bugmessage.message = message.id
        AND messagechunk.message = message.id
        AND messagechunk.sequence = 1
    ORDER BY messagechunk.id
    LIMIT 1
    )
WHERE description IS NULL OR trim(from description) = '';

ALTER TABLE Bug ALTER COLUMN description SET NOT NULL;
ALTER TABLE Bug ADD CONSTRAINT no_empty_desctiption
    CHECK (trim(from description) <> '');

INSERT INTO LaunchpadDatabaseRevision VALUES (25, 19, 0);

