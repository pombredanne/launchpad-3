
set client_min_messages=ERROR;

/* dealing with a NULL priority is just a pain in the nexk that results in
 * unnecessarily complicated TAL. */

UPDATE Specification SET priority=5 WHERE priority IS NULL;
ALTER TABLE Specification ALTER COLUMN priority SET DEFAULT 5;
ALTER TABLE Specification ALTER COLUMN priority SET NOT NULL;

INSERT INTO LaunchpadDatabaseRevision VALUES (25,77,0);
