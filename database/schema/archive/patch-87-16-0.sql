SET client_min_messages=ERROR;

/*
 * Extra PPA maintenance fields for Archive table.
 */


ALTER TABLE Archive ADD COLUMN enabled BOOLEAN DEFAULT TRUE NOT NULL;

ALTER TABLE Archive ADD COLUMN authorized_size INTEGER;

ALTER TABLE Archive ADD COLUMN whiteboard TEXT;

UPDATE Archive SET enabled=TRUE, authorized_size=104857600
   WHERE Archive.owner IS NOT NULL;


INSERT INTO LaunchpadDatabaseRevision VALUES (87, 16, 0);

