SET client_min_messages=ERROR;

CREATE TRIGGER you_are_your_own_member AFTER INSERT ON Person
    FOR EACH ROW EXECUTE PROCEDURE you_are_your_own_member();

INSERT INTO TeamParticipation (person, team) (
    SELECT id, id FROM Person
    WHERE teamowner IS NULL
        AND id NOT IN (SELECT person FROM TeamParticipation WHERE person=team)
    );

INSERT INTO LaunchpadDatabaseRevision VALUES (11,6,0);

