-- Copyright 2009 Canonical Ltd.  This software is licensed under the
-- GNU Affero General Public License version 3 (see the file LICENSE).

SET client_min_messages=ERROR;

CREATE TABLE AuthToken (
    id serial PRIMARY KEY,
    date_created timestamp without time zone NOT NULL
        DEFAULT (CURRENT_TIMESTAMP AT TIME ZONE 'UTC'),
    date_consumed timestamp without time zone,
    token_type integer NOT NULL,
    token text NOT NULL CONSTRAINT authtoken__token__key UNIQUE,
    requester integer CONSTRAINT authtoken__requester__fk REFERENCES Account,
    requester_email text,
    email text NOT NULL,
    redirection_url text
);

-- For garbage collection
CREATE INDEX authtoken__date_created__idx ON AuthToken(date_created);
CREATE INDEX authtoken__date_consumed__idx ON AuthToken(date_consumed);

CREATE INDEX authtoken__requester__idx ON AuthToken(requester);

INSERT INTO LaunchpadDatabaseRevision VALUES (2109, 21, 0);
