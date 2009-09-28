SET client_min_messages TO ERROR;

UPDATE BugActivity SET person=(SELECT id FROM Person WHERE name='janitor')
WHERE person NOT IN (SELECT id FROM Person);

ALTER TABLE BugActivity
    ADD CONSTRAINT bugactivity__person__fk
    FOREIGN KEY (person) REFERENCES Person;

INSERT INTO LaunchpadDatabaseRevision VALUES (2207, 0, 3);

