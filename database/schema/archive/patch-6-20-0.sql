
SET client_min_messages=ERROR;

CREATE TABLE LoginToken (
    id serial,
    requester integer,
    requesteremail text,
    email text NOT NULL,
    created timestamp DEFAULT (current_timestamp AT TIME ZONE 'UTC') NOT NULL,
    tokentype integer NOT NULL,
    token text UNIQUE,
    CONSTRAINT logintoken_requester_fk FOREIGN KEY (requester) REFERENCES Person
   );
CREATE INDEX logintoken_requester_idx ON LoginToken(requester);

UPDATE LaunchpadDatabaseRevision SET major=6, minor=20, patch=0;

