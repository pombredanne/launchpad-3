-- Create TeamParticipation entries to make teams be members of themselves.
INSERT INTO TeamParticipation (person, team)
    (SELECT id, id FROM Person WHERE teamowner IS NOT NULL);
