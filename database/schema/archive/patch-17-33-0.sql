SET client_min_messages=ERROR;

CREATE TABLE KarmaAction (
    id serial PRIMARY KEY,
    name integer NOT NULL CONSTRAINT karmaaction_name_key UNIQUE,
    category integer,
    points integer
);

CREATE TABLE KarmaCache (
    id serial NOT NULL PRIMARY KEY,
    person integer NOT NULL,
    category integer NOT NULL,
    karmavalue integer NOT NULL,
    CONSTRAINT person_fk FOREIGN KEY (person) REFERENCES person(id),
    CONSTRAINT category_person_key UNIQUE (category, person)
);

DELETE FROM Karma;

ALTER TABLE Karma DROP COLUMN points;
ALTER TABLE Karma DROP COLUMN karmatype;
ALTER TABLE Karma ALTER COLUMN datecreated
    SET DEFAULT CURRENT_TIMESTAMP AT TIME ZONE 'UTC';
ALTER TABLE Karma ADD COLUMN action integer;


ALTER TABLE Karma ALTER COLUMN action SET NOT NULL;
ALTER TABLE Karma ADD CONSTRAINT action_fkey FOREIGN KEY (action) REFERENCES KarmaAction(id);

ALTER TABLE Person DROP COLUMN karma;
ALTER TABLE Person DROP COLUMN karmatimestamp;

CREATE INDEX karma_person_datecreated_idx ON Karma(person, datecreated);

INSERT INTO LaunchpadDatabaseRevision VALUES (17, 33, 0);
