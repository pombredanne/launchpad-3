SET client_min_messages=ERROR;

ALTER TABLE TeamMembership 
    ADD COLUMN proposed_by integer REFERENCES Person;
ALTER TABLE TeamMembership 
    ADD COLUMN acknowledged_by integer REFERENCES Person;
ALTER TABLE TeamMembership 
    ADD COLUMN reviewed_by integer REFERENCES Person;
ALTER TABLE TeamMembership
    ADD COLUMN date_proposed timestamp without time zone;
ALTER TABLE TeamMembership
    ADD COLUMN date_last_changed timestamp without time zone;
ALTER TABLE TeamMembership
    ADD COLUMN date_acknowledged timestamp without time zone;
ALTER TABLE TeamMembership
    ADD COLUMN date_reviewed timestamp without time zone;
ALTER TABLE TeamMembership
    ADD COLUMN proponent_comment text;
ALTER TABLE TeamMembership
    ADD COLUMN acknowledger_comment text;
ALTER TABLE TeamMembership
    ADD COLUMN reviewer_comment text;

CREATE INDEX teammembership__proposed_by__idx 
    ON TeamMembership(proposed_by) WHERE proposed_by IS NOT NULL;
CREATE INDEX teammembership__acknowledged_by__idx 
    ON TeamMembership(acknowledged_by) WHERE acknowledged_by IS NOT NULL;
CREATE INDEX teammembership__reviewed_by__idx 
    ON TeamMembership(reviewed_by) WHERE reviewed_by IS NOT NULL;

-- Leave this as a NULLable column for now as we'll update its values later
-- and that will take a long time, I think.
ALTER TABLE TeamMembership ADD COLUMN date_created timestamp without time zone
        DEFAULT (CURRENT_TIMESTAMP AT TIME ZONE 'UTC');

ALTER TABLE TeamMembership 
    RENAME COLUMN reviewer TO last_changed_by;
ALTER TABLE TeamMembership
    RENAME COLUMN reviewercomment TO last_change_comment;

-- Rename some columns to match current naming standards.
ALTER TABLE TeamMembership RENAME COLUMN datejoined TO date_joined;
ALTER TABLE TeamMembership RENAME COLUMN dateexpires TO date_expires;

-- We've changed the semantics of date_joined so it's now NULLable.
ALTER TABLE TeamMembership ALTER COLUMN date_joined DROP NOT NULL;

INSERT INTO LaunchpadDatabaseRevision VALUES (121, 17, 0);
