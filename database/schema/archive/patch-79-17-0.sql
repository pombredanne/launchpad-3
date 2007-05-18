SET client_min_messages=ERROR;

CREATE TABLE ScriptActivity (
  id serial NOT NULL,
  name text NOT NULL,
  hostname text NOT NULL,
  date_started timestamp without time zone NOT NULL,
  date_completed timestamp without time zone NOT NULL
);

INSERT INTO LaunchpadDatabaseRevision VALUES (79, 17, 0);

