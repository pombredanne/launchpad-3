SET client_min_messages=ERROR;

ALTER TABLE TeamMembership 
    ADD COLUMN proposed_by integer REFERENCES Person,
    ADD COLUMN acknowledged_by integer REFERENCES Person,
    ADD COLUMN reviewed_by integer REFERENCES Person,
    ADD COLUMN date_proposed timestamp without time zone,
    ADD COLUMN date_last_changed timestamp without time zone,
    ADD COLUMN date_acknowledged timestamp without time zone,
    ADD COLUMN date_reviewed timestamp without time zone,
    ADD COLUMN proponent_comment text,
    ADD COLUMN acknowledger_comment text,
    ADD COLUMN reviewer_comment text,
    ADD COLUMN date_created timestamp without time zone;

-- Populate date_created as best we can.
UPDATE TeamMembership SET date_created = greatest(
    datejoined, Person.datecreated, Team.datecreated)
FROM Person AS Team, Person AS Person
WHERE
    TeamMembership.person <> TeamMembership.team
    AND TeamMembership.team = Team.id AND TeamMembership.person = Person.id;
UPDATE TeamMembership SET date_created = datecreated
FROM Person
WHERE
    TeamMembership.person = TeamMembership.team
    AND TeamMembership.person = Person.id;
ALTER TABLE TeamMembership ALTER COLUMN date_created
    SET DEFAULT CURRENT_TIMESTAMP AT TIME ZONE 'UTC';
ALTER TABLE TeamMembership ALTER COLUMN date_created SET NOT NULL;

ALTER TABLE TeamMembership 
    RENAME COLUMN reviewer TO last_changed_by;
ALTER TABLE TeamMembership
    RENAME COLUMN reviewercomment TO last_change_comment;

CREATE INDEX teammembership__proposed_by__idx 
    ON TeamMembership(proposed_by) WHERE proposed_by IS NOT NULL;
CREATE INDEX teammembership__acknowledged_by__idx 
    ON TeamMembership(acknowledged_by) WHERE acknowledged_by IS NOT NULL;
CREATE INDEX teammembership__reviewed_by__idx 
    ON TeamMembership(reviewed_by) WHERE reviewed_by IS NOT NULL;
CREATE INDEX teammembership__last_changed_by__idx
    ON TeamMembership(last_changed_by) WHERE last_changed_by IS NOT NULL;

-- Rename some columns to match current naming standards.
ALTER TABLE TeamMembership RENAME COLUMN datejoined TO date_joined;
ALTER TABLE TeamMembership RENAME COLUMN dateexpires TO date_expires;

-- We've changed the semantics of date_joined so it's now NULLable.
ALTER TABLE TeamMembership ALTER COLUMN date_joined DROP NOT NULL;

-- Set proposed_by and date_proposed for memberships in the INVITED and
-- PROPOSED state.
UPDATE TeamMembership 
    SET proposed_by = last_changed_by, date_proposed = date_joined
    WHERE status IN (1, 7);

INSERT INTO LaunchpadDatabaseRevision VALUES (121, 17, 0);
