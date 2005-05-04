SET client_min_messages=ERROR;

CREATE TABLE MessageChunk (
    id serial PRIMARY KEY,
    message integer
        CONSTRAINT messagechunk_message_fk REFERENCES Message NOT NULL,
    sequence integer NOT NULL,
    content text,
    blob integer CONSTRAINT messagechunk_blob_fk REFERENCES LibraryFileAlias,
    CONSTRAINT text_or_content CHECK (
        (blob IS NULL and content IS NULL) OR (blob IS NULL <> content IS NULL)
        ),
    CONSTRAINT messagechunk_message_idx UNIQUE (message, sequence)
    );

INSERT INTO MessageChunk(message, sequence, content)
    SELECT id, 1, contents
    FROM Message;

ALTER TABLE Message DROP COLUMN contents;
ALTER TABLE Message ADD COLUMN "raw" integer 
    CONSTRAINT message_raw_fk REFERENCES LibraryFileAlias;

INSERT INTO LaunchpadDatabaseRevision VALUES (14, 2, 0);

