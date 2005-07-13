
/* Create tables to cache the level of translation of the whole distro
   release. */

SET client_min_messages=ERROR;

ALTER TABLE DistroRelease ADD COLUMN messagecount integer;
UPDATE DistroRelease SET messagecount=0;
ALTER TABLE DistroRelease ALTER COLUMN messagecount SET DEFAULT 0;
ALTER TABLE DistroRelease ALTER COLUMN messagecount SET NOT NULL;

CREATE TABLE DistroReleaseLanguage (
  id               serial PRIMARY KEY,
  distrorelease    integer CONSTRAINT distroreleaselanguage_distrorelease_fk
                           REFERENCES DistroRelease,
  language         integer CONSTRAINT distroreleaselanguage_language_fk
                           REFERENCES Language,
  currentcount     integer NOT NULL,
  updatescount     integer NOT NULL,
  rosettacount     integer NOT NULL,
  contributorcount integer NOT NULL,
  dateupdated      timestamp without time zone 
                   DEFAULT (CURRENT_TIMESTAMP AT TIME ZONE 'UTC') NOT NULL
);

INSERT INTO LaunchpadDatabaseRevision VALUES (17, 41, 0);

