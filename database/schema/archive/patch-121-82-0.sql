SET client_min_messages=ERROR;

CREATE TABLE BugAffectsPerson (
    id SERIAL PRIMARY KEY,
    bug INTEGER NOT NULL REFERENCES Bug(id),
    person INTEGER NOT NULL REFERENCES Person(id),
    CONSTRAINT bugaffectsperson_bug_person_uniq UNIQUE (bug, person)
);

CREATE INDEX bugaffectsperson__person__idx ON BugAffectsPerson(person);

ALTER TABLE Bug
    ADD COLUMN users_affected_count INTEGER DEFAULT 0;

CREATE INDEX bug__users_affected_count__idx ON Bug(users_affected_count);

CREATE TRIGGER set_bug_users_affected_count_t
    AFTER INSERT OR DELETE ON BugAffectsPerson
    FOR EACH ROW
    EXECUTE PROCEDURE set_bug_users_affected_count();

INSERT INTO LaunchpadDatabaseRevision VALUES (121, 82, 0);
