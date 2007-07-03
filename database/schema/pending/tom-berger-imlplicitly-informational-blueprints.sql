SET client_min_messages = ERROR;

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

ALTER TABLE specification
ADD CONSTRAINT specification_start_recorded_chk
CHECK ((date_started IS NULL) <>
       (implementation_status <> 0 AND
        implementation_status <> 5 AND
        implementation_status <> 10));
