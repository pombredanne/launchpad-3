SET client_min_messages=ERROR;

ALTER TABLE Bug ADD CONSTRAINT bug_owner_fk
    FOREIGN KEY(owner) REFERENCES Person;

ALTER TABLE Bug DROP CONSTRAINT "$1";
ALTER TABLE Bug ADD CONSTRAINT bug_duplicateof_fk
    FOREIGN KEY(duplicateof) REFERENCES Bug;

INSERT INTO LaunchpadDatabaseRevision VALUES (14, 11, 0);

