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


  -- Keep track of the full lifecycle of sprint agenda
ALTER TABLE SprintSpecification ADD COLUMN date_created
    timestamp without time zone;
UPDATE SprintSpecification SET date_created = 'NOW';
ALTER TABLE SprintSpecification ALTER COLUMN date_created
    SET DEFAULT (CURRENT_TIMESTAMP AT TIME ZONE 'UTC');
ALTER TABLE SprintSpecification ALTER COLUMN date_created SET NOT NULL;
ALTER TABLE SprintSpecification RENAME COLUMN nominator TO registrant;
UPDATE SprintSpecification SET registrant = Specification.owner
    FROM Specification
    WHERE SprintSpecification.specification = Specification.id;
ALTER TABLE SprintSpecification ALTER COLUMN registrant SET NOT NULL;
ALTER TABLE SprintSpecification ADD COLUMN decider integer;
ALTER TABLE SprintSpecification
    ADD CONSTRAINT sprintspecification_decider_fk FOREIGN KEY (decider)
    REFERENCES Person(id);
ALTER TABLE SprintSpecification ADD COLUMN date_decided
    timestamp without time zone;
UPDATE SprintSpecification
    SET decider=Sprint.owner, date_decided=date_created 
    FROM Sprint
    WHERE SprintSpecification.sprint=Sprint.id AND
          SprintSpecification.status <> 30;
ALTER TABLE SprintSpecification
    ADD CONSTRAINT sprintspecification_decision_recorded
    CHECK ((status = 30 OR (decider IS NOT NULL and date_decided IS NOT NULL)));

  -- Track the full lifecycle of nomination and approval of specs to a
  -- series goal

  -- first keep track of who nominated a spec for a series
ALTER TABLE Specification ADD COLUMN goal_proposer integer;
ALTER TABLE Specification ADD CONSTRAINT specification_goal_proposer_fk
    FOREIGN KEY (goal_proposer) REFERENCES Person(id);
UPDATE Specification SET goal_proposer=owner
    WHERE productseries IS NOT NULL OR distrorelease IS NOT NULL;

  -- and when they did so
ALTER TABLE Specification ADD COLUMN date_goal_proposed
    timestamp without time zone;
UPDATE Specification SET date_goal_proposed='NOW'
    WHERE productseries IS NOT NULL OR distrorelease IS NOT NULL;

  -- ensure that this information is available for any spec which has
  -- been nominated for a goal
ALTER TABLE Specification ADD CONSTRAINT specification_goal_nomination_chk
    CHECK ((productseries IS NULL AND distrorelease IS NULL) OR 
           (goal_proposer IS NOT NULL AND date_goal_proposed IS NOT NULL));

  -- now let's keep track of the person who approved or declined the spec
ALTER TABLE Specification ADD COLUMN goal_decider integer;
ALTER TABLE Specification ADD CONSTRAINT specification_goal_decider_fk
    FOREIGN KEY (goal_decider) REFERENCES Person(id);

  -- and when they did it
ALTER TABLE Specification ADD COLUMN date_goal_decided
    timestamp without time zone;

  -- let's guess who would have approved existing goals and when
UPDATE Specification
    SET goal_decider=owner, date_goal_decided=datecreated 
    WHERE Specification.goalstatus <> 30;

ALTER TABLE Specification
    ADD CONSTRAINT specification_decision_recorded
    CHECK ((goalstatus = 30 OR
           (goal_decider IS NOT NULL and date_goal_decided IS NOT NULL)));


INSERT INTO LaunchpadDatabaseRevision VALUES (67, 97, 0);
