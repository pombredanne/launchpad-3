SET client_min_messages=ERROR;

ALTER TABLE PersonLocation ADD CONSTRAINT latitude_and_longitude_together
  CHECK ((latitude IS NULL) = (longitude IS NULL));

CREATE TABLE PersonNotification (
  id serial PRIMARY KEY,
  person integer NOT NULL REFERENCES Person(id),
  date_created timestamp without time zone NOT NULL
               DEFAULT (CURRENT_TIMESTAMP AT TIME ZONE 'UTC'),
  date_emailed timestamp without time zone,
  body text NOT NULL,
  subject text NOT NULL
);

CREATE INDEX personnotification__person__idx
          ON PersonNotification(person);
CREATE INDEX personnotification__date_emailed__idx
          ON PersonNotification(date_emailed);

INSERT INTO LaunchpadDatabaseRevision VALUES (121, 49, 0);
