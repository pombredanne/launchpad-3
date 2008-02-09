SET client_min_messages=ERROR;

CREATE TABLE PersonLocation (
    id serial PRIMARY KEY,
    date_created TIMESTAMP WITHOUT TIME ZONE NOT NULL
                 DEFAULT timezone('UTC'::text, now()),
    person integer NOT NULL UNIQUE REFERENCES Person(id),
    latitude float,
    longitude float,
    time_zone text NOT NULL,
    last_modified_by integer NOT NULL REFERENCES Person(id),
    date_last_modified TIMESTAMP WITHOUT TIME ZONE NOT NULL
                DEFAULT timezone('UTC'::text, now())
    );

INSERT INTO PersonLocation
       (person, time_zone, last_modified_by, date_last_modified)
       SELECT id, timezone, id, 'NOW'::timestamp without time zone
       FROM Person WHERE timezone != 'UTC'::text;

ALTER TABLE Person DROP COLUMN timezone;

INSERT INTO LaunchpadDatabaseRevision VALUES (88, 44, 0);
