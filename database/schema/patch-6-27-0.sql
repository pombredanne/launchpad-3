/* Table for authserver to support sftp service  to the supermirror */

SET client_min_messages=ERROR;

CREATE TABLE PushMirrorAccess (
    id          serial PRIMARY KEY,
    name        text NOT NULL UNIQUE,
    person      integer REFERENCES Person
);

CREATE INDEX pushmirroraccess_person_idx ON PushMirrorAccess(person);

UPDATE LaunchpadDatabaseRevision SET major=6, minor=27, patch=0;

