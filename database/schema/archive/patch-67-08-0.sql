SET client_min_messages=ERROR;

/* Blueprint Updates
   A series of small fixes to the Blueprint data model to address minor
   issues that have arisen since the Edgy sprint in Paris.
*/

  -- Allow for recording if someone is essential to a spec discussions
ALTER TABLE SpecificationSubscription
    ADD COLUMN essential boolean DEFAULT FALSE;
UPDATE SpecificationSubscription SET essential=FALSE;
ALTER TABLE SpecificationSubscription ALTER COLUMN essential SET NOT NULL;

  -- Needs discussion is now a database status and not needed as a
  -- separate column
UPDATE Specification SET status=35 WHERE needs_discussion IS TRUE AND status=30;
ALTER TABLE Specification DROP COLUMN needs_discussion;

  -- Meetings and sprints also need "drivers", people who decide what
  -- specs will be on the agenda
ALTER TABLE Sprint ADD COLUMN driver integer REFERENCES Person(id);
CREATE INDEX sprint__driver__idx ON Sprint(driver);

  -- Keep track of the full lifecycle of sprint agenda
ALTER TABLE SprintSpecification
    ADD COLUMN date_created timestamp without time zone
    DEFAULT (CURRENT_TIMESTAMP AT TIME ZONE 'UTC');

UPDATE SprintSpecification SET date_created = DEFAULT;
ALTER TABLE SprintSpecification ALTER COLUMN date_created SET NOT NULL;

DROP INDEX sprintspecification__nominator__idx;
ALTER TABLE SprintSpecification RENAME COLUMN nominator TO registrant;
UPDATE SprintSpecification SET registrant = Specification.owner
    FROM Specification
    WHERE SprintSpecification.specification = Specification.id;
ALTER TABLE SprintSpecification ALTER COLUMN registrant SET NOT NULL;
CREATE INDEX sprintspecification__registrant__idx ON SprintSpecification(registrant);

ALTER TABLE SprintSpecification ADD COLUMN decider integer
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
CREATE INDEX sprintspecification__decider__idx ON SprintSpecification(decider);


  -- Track the full lifecycle of nomination and approval of specs to a
  -- series goal

  -- first keep track of who nominated a spec for a series
ALTER TABLE Specification ADD COLUMN goal_proposer integer
    REFERENCES Person(id);
UPDATE Specification SET goal_proposer=owner
    WHERE productseries IS NOT NULL OR distrorelease IS NOT NULL;
CREATE INDEX specification__goal_proposer__idx ON Specification(goal_proposer);

  -- and when they did so
ALTER TABLE Specification ADD COLUMN date_goal_proposed
    timestamp without time zone;
UPDATE Specification
    SET date_goal_proposed=CURRENT_TIMESTAMP AT TIME ZONE 'UTC'
    WHERE productseries IS NOT NULL OR distrorelease IS NOT NULL;

  -- ensure that this information is available for any spec which has
  -- been nominated for a goal
ALTER TABLE Specification ADD CONSTRAINT specification_goal_nomination_chk
    CHECK ((productseries IS NULL AND distrorelease IS NULL) OR
           (goal_proposer IS NOT NULL AND date_goal_proposed IS NOT NULL));

  -- now let's keep track of the person who approved or declined the spec
ALTER TABLE Specification ADD COLUMN goal_decider integer
    REFERENCES Person(id);
CREATE INDEX specification__goal_decider__idx ON Specification(goal_decider);

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


-- keep track of the date-of-resolution of a specification, so we know
-- when it was either implemented, or market superseded/obsolete, or
-- approved as an informational specification

ALTER TABLE Specification ADD COLUMN completer integer
    REFERENCES Person(id);
ALTER TABLE Specification ADD COLUMN date_completed
    timestamp without time zone;
  -- set it to NOW for specs which are currently resolved
UPDATE Specification
    SET date_completed=CURRENT_TIMESTAMP AT TIME ZONE 'UTC', completer=owner
    WHERE date_completed IS NULL AND
              (delivery = 90 OR
               status IN ( 60, 70 ) OR
               (informational IS TRUE AND status = 10));
  -- put a check constraint in place to ensure we don't forget to mark
  -- specs completed when appropriate
ALTER TABLE Specification ADD CONSTRAINT specification_completion_recorded_chk
    CHECK ((date_completed IS NULL) <>
           (delivery = 90 OR
            status IN ( 60, 70 ) OR
            (informational IS TRUE AND status = 10)));
ALTER TABLE Specification
    ADD CONSTRAINT specification_completion_fully_recorded_chk
    CHECK ((date_completed IS NULL) = (completer IS NULL));
CREATE INDEX specification__completer__idx ON Specification(completer);

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

INSERT INTO LaunchpadDatabaseRevision VALUES (67, 8, 0);

