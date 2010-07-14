SET client_min_messages=ERROR;

DELETE FROM bugsubscription WHERE id NOT IN (
    SELECT MIN(dup.id) FROM
    bugsubscription AS dup 
    GROUP BY dup.person, dup.bug);

ALTER TABLE BugSubscription ADD CONSTRAINT bugsubscription__person__bug__key
    UNIQUE (person, bug);

INSERT INTO LaunchpadDatabaseRevision VALUES (2207, 67, 0);

