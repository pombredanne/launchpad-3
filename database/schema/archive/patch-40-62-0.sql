SET client_min_messages=ERROR;

/* Keep track of the person who nominated a spec for a meeting agenda */

ALTER TABLE SprintSpecification ADD COLUMN nominator integer;
ALTER TABLE SprintSpecification
    ADD CONSTRAINT sprintspecification__nominator__fk
    FOREIGN KEY (nominator) REFERENCES Person(id);
CREATE INDEX sprintspecification__nominator__idx
    ON SprintSpecification(nominator);

INSERT INTO LaunchpadDatabaseRevision VALUES (40, 62, 0);

