SET client_min_messages=ERROR;

-- keep track of the date the spec was started, and by whom

ALTER TABLE Specification ADD COLUMN starter integer
    REFERENCES Person(id);
ALTER TABLE Specification ADD COLUMN date_started
    timestamp without time zone;
  -- set it to NOW for specs which are currently started
UPDATE Specification
    SET date_started=CURRENT_TIMESTAMP AT TIME ZONE 'UTC', starter=owner
    WHERE date_started IS NULL AND
              (delivery NOT IN ( 0, 5, 10 ) OR
               (informational IS TRUE AND status = 10));
  -- put a check constraint in place to ensure we don't forget to mark
  -- specs started when appropriate
ALTER TABLE Specification ADD CONSTRAINT specification_start_recorded_chk
    CHECK ((date_started IS NULL) <>
           (delivery NOT IN ( 0, 5, 10 ) OR
            (informational IS TRUE AND status = 10)));
ALTER TABLE Specification
    ADD CONSTRAINT specification_start_fully_recorded_chk
    CHECK ((date_started IS NULL) = (starter IS NULL));
CREATE INDEX specification__starter__idx ON Specification(starter);

INSERT INTO LaunchpadDatabaseRevision VALUES (67, 93, 0);
