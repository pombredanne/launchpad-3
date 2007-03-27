SET client_min_messages=ERROR;

CREATE TABLE ScriptActivity (
  id serial NOT NULL,
  name text NOT NULL,
  hostname text NOT NULL,
  date_started timestamp without time zone NOT NULL
    DEFAULT (current_timestamp AT TIME ZONE 'UTC'),
  date_completed timestamp without time zone NOT NULL
    DEFAULT (current_timestamp AT TIME ZONE 'UTC'),
  status integer NOT NULL DEFAULT 0
);

INSERT INTO LaunchpadDatabaseRevision VALUES (79, 95, 0);

