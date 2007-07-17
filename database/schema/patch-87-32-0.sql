SET client_min_messages=ERROR;

ALTER TABLE specification
DROP CONSTRAINT specification_start_recorded_chk;

ALTER TABLE specification
RENAME COLUMN status TO definition_status;

ALTER TABLE specification
RENAME COLUMN delivery TO implementation_status;

UPDATE Specification
SET implementation_status = 95
WHERE informational IS TRUE;

ALTER TABLE specification
DROP COLUMN informational;

/* Temporarily disabled -- StuartBishop 20070716

ALTER TABLE Specification ADD CONSTRAINT specification_start_recorded_chk
CHECK ((date_started IS NULL) <>
       (implementation_status NOT IN ( 0, 5, 10, 95 ) OR
       (implementation_status = 95 AND definition_status = 10)));
*/

INSERT INTO LaunchpadDatabaseRevision VALUES (87, 32, 0);

