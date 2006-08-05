SET client_min_messages=ERROR;

/* Blueprint Updates
   A series of small fixes to the Blueprint data model to address minor
   issues that have arisen since the Edgy sprint in Paris.
*/

  -- Allow for recording if someone is essential to a spec discussions
ALTER TABLE SpecificationSubscription ADD COLUMN essential boolean;
UPDATE SpecificationSubscription SET essential=FALSE;
ALTER TABLE SpecificationSubscription ALTER COLUMN essential SET DEFAULT False; 
ALTER TABLE SpecificationSubscription ALTER COLUMN essential SET NOT NULL; 

  -- Needs discussion is now a database status and not needed as a
  -- separate column
UPDATE Specification SET status=35 WHERE needs_discussion IS TRUE AND status=30;
ALTER TABLE Specification DROP COLUMN needs_discussion;

  -- Meetings and sprints also need "drivers", people who decide what
  -- specs will be on the agenda
ALTER TABLE Sprint ADD COLUMN driver integer;
ALTER TABLE Sprint ADD CONSTRAINT sprint_driver_fk FOREIGN KEY (driver)
    REFERENCES Person(id);

INSERT INTO LaunchpadDatabaseRevision VALUES (67, 97, 0);
