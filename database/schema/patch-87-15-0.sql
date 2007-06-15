SET client_min_messages=ERROR;

ALTER TABLE Person ADD COLUMN openid_identifier text UNIQUE;

-- Give users in the openid-testers team an openid_identifier
-- (Ideally we would give everyone one right now, but that takes over 5 hours)
CREATE TRIGGER temp_t_set_openid_identifier BEFORE UPDATE ON Person
FOR EACH ROW EXECUTE PROCEDURE set_openid_identifier();
UPDATE Person SET openid_identifier=NULL
    FROM TeamParticipation, Person AS Team
    WHERE Person.id = TeamParticipation.person
        AND TeamParticipation.team = Team.id
        AND Team.name = 'openid-testers'
        AND Person.openid_identifier IS NULL;
-- Drop this trigger when we have populated everyone's openid_identifier
-- and set the column to NOT NULL.
--DROP TRIGGER temp_t_set_openid_identifier ON Person;

-- We should make the openid_identifier column required, but we can't yet.
-- ALTER TABLE Person ALTER COLUMN openid_identifier SET NOT NULL;

-- Add a trigger so the new column is always filled in on creation
CREATE TRIGGER set_openid_identifier_t BEFORE INSERT ON Person
FOR EACH ROW EXECUTE PROCEDURE set_openid_identifier();

INSERT INTO LaunchpadDatabaseRevision VALUES (87, 15, 0);
