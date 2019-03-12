-- Copyright 2015 Canonical Ltd.  This software is licensed under the
-- GNU Affero General Public License version 3 (see the file LICENSE).

SET client_min_messages=ERROR;

CREATE TABLE XRef (
    from_type text NOT NULL,
    from_id text NOT NULL,
    from_id_int integer,
    to_type text NOT NULL,
    to_id text NOT NULL,
    to_id_int integer,
    creator integer REFERENCES Person,
    date_created timestamp without time zone
        DEFAULT (CURRENT_TIMESTAMP AT TIME ZONE 'UTC') NOT NULL,
    metadata text,
    PRIMARY KEY (from_type, from_id, to_type, to_id)
);

CREATE UNIQUE INDEX xref__inverse__key
    ON XRef(to_type, to_id, from_type, from_id);
CREATE UNIQUE INDEX xref__int__key
    ON XRef(from_type, from_id_int, to_type, to_id_int);
CREATE UNIQUE INDEX xref__int_inverse__key
    ON XRef(to_type, to_id_int, from_type, from_id_int);
CREATE INDEX xref__from_type__to_type__idx ON XRef(from_type, to_type);
CREATE INDEX xref__to_type__from_type__idx ON XRef(to_type, from_type);

CREATE INDEX xref__creator__idx ON XRef(creator);

INSERT INTO LaunchpadDatabaseRevision VALUES (2209, 70, 0);
