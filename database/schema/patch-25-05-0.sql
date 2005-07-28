
set client_min_messages=ERROR;

CREATE TABLE LaunchpadStatistic (
  id            serial PRIMARY KEY,
  name          text NOT NULL,
  value         integer NOT NULL,
  dateupdated   timestamp WITHOUT TIME ZONE NOT NULL
                DEFAULT (CURRENT_TIMESTAMP AT TIME ZONE 'UTC')
);
ALTER TABLE LaunchpadStatistic ADD CONSTRAINT
launchpadstatistics_uniq_name UNIQUE (name);

INSERT INTO LaunchpadDatabaseRevision VALUES (25,5,0);

