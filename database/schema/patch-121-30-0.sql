SET client_min_messages=ERROR;

CREATE TRIGGER t_assert_self_membership
    AFTER DELETE ON TeamParticipation
    FOR EACH ROW EXECUTE PROCEDURE assert_self_membership();

INSERT INTO LaunchpadDatabaseRevision VALUES (121, 30, 0);
