SET client_min_messages=ERROR;

CREATE TABLE KarmaTotalCache (
    id serial primary key,
    person integer NOT NULL
        CONSTRAINT karmatotalcache_person_fk REFERENCES Person
        ON DELETE CASCADE,
    karma_total integer NOT NULL
    ) WITHOUT OIDS;

INSERT INTO KarmaTotalCache (person, karma_total)
    SELECT person, SUM(karmavalue)
    FROM KarmaCache
    GROUP BY person;

ALTER TABLE KarmaTotalCache ADD CONSTRAINT karmatotalcache_person_key
    UNIQUE (person);

CREATE UNIQUE INDEX karmatotalcache_karma_total_person_idx
    ON KarmaTotalCache(karma_total, person);

ALTER TABLE Person DROP COLUMN karma;

INSERT INTO LaunchpadDatabaseRevision VALUES (40, 15, 0);

