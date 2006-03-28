SET client_min_messages=ERROR;

-- Description IS NOT NULL so we don't need to worry about foo || NULL == NULL
UPDATE Bug SET description = summary || '\n\n' || description
    WHERE summary IS NOT NULL;
ALTER TABLE Bug DROP COLUMN summary;

INSERT INTO LaunchpadDatabaseRevision VALUES (40, 32, 0);
