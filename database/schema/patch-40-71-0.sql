set client_min_messages=ERROR;

/* Rosetta Template Priorities

   Keep track of which templates are more important than others for
   translation purposes.
*/

UPDATE POTemplate SET priority=0 WHERE priority IS NULL;
ALTER TABLE POTemplate ALTER COLUMN priority SET DEFAULT 0;
ALTER TABLE POTemplate ALTER COLUMN priority SET NOT NULL;

INSERT INTO LaunchpadDatabaseRevision VALUES (40, 71, 0);
