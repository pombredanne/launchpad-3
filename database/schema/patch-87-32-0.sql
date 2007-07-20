SET client_min_messages=ERROR;

ALTER TABLE specification
DROP CONSTRAINT specification_start_recorded_chk;

ALTER TABLE specification
DROP CONSTRAINT specification_completion_recorded_chk;

ALTER TABLE specification
RENAME COLUMN status TO definition_status;

ALTER TABLE specification
RENAME COLUMN delivery TO implementation_status;

UPDATE Specification
SET implementation_status = 95
WHERE informational IS TRUE;

ALTER TABLE specification
DROP COLUMN informational;

UPDATE Specification
SET date_started = NULL, starter=NULL
WHERE NOT ((implementation_status NOT IN ( 0, 5, 10, 95 ) OR
           (implementation_status = 95 AND definition_status = 10)));

UPDATE Specification
SET date_completed = NULL,
    completer = NULL
WHERE NOT ((implementation_status = 90 OR definition_status IN (60, 70)) OR
           (implementation_status = 95 AND definition_status = 10));

ALTER TABLE Specification ADD CONSTRAINT specification_start_recorded_chk
CHECK ((date_started IS NULL) <>
       (implementation_status NOT IN ( 0, 5, 10, 95 ) OR
       (implementation_status = 95 AND definition_status = 10)));

ALTER TABLE Specification ADD CONSTRAINT specification_completion_recorded_chk
CHECK ((date_completed IS NULL) <> 
        ((implementation_status = 90 OR definition_status IN (60, 70)) OR
         (implementation_status = 95 AND definition_status = 10)));

INSERT INTO LaunchpadDatabaseRevision VALUES (87, 32, 0);

