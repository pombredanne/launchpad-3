SET client_min_messages=ERROR;

/*  Delete any Karma that has been assigned to a team */
DELETE FROM Karma WHERE person IN (
    SELECT id FROM Person WHERE teamowner IS NOT NULL
    );

/* Delete any Karma that has been assigned to an invalid person */
DELETE FROM Karma WHERE person NOT IN (
    SELECT id FROM ValidPersonOrTeamCache
    );

INSERT INTO LaunchpadDatabaseRevision VALUES (40, 34, 0);

