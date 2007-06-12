/*
 * Extra PPA maintenance fields for Archive table.
 */

SET client_min_messages=ERROR;

ALTER TABLE Archive
    ADD COLUMN enabled BOOLEAN;

ALTER TABLE Archive
    ADD COLUMN authorized_size INTEGER;

ALTER TABLE Archive
    ADD COLUMN whiteboard TEXT;

UPDATE Archive
   SET enabled=true, authorized_size=52428800
   WHERE Archive.owner <> null;


INSERT INTO LaunchpadDatabaseRevision VALUES (87, 99, 0);