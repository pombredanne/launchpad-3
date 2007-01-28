SET client_min_messages=ERROR;

/* Create a place to store temporary blobs of data. This is used by programs
   that want, for example, to launchpad a browser to file  a bug, and want
   to position a blob of data in the system before they do so.
*/

CREATE TABLE TemporaryBlobStorage (
  id                serial PRIMARY KEY,
  uuid              text NOT NULL UNIQUE,
  date_created      timestamp without time zone NOT NULL
                        DEFAULT (CURRENT_TIMESTAMP AT TIME ZONE 'UTC'),
  file_alias        int NOT NULL UNIQUE REFERENCES LibraryFileAlias
  );

INSERT INTO LaunchpadDatabaseRevision VALUES (67, 32, 0);

