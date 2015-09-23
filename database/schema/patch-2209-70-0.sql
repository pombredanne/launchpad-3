-- Copyright 2015 Canonical Ltd.  This software is licensed under the
-- GNU Affero General Public License version 3 (see the file LICENSE).

SET client_min_messages=ERROR;

CREATE TABLE XRef (
    type1 text NOT NULL,
    id1 text NOT NULL,
    id1_int integer,
    type2 text NOT NULL,
    id2 text NOT NULL,
    id2_int integer,
    creator integer REFERENCES Person,
    date_created timestamp without time zone
        DEFAULT (CURRENT_TIMESTAMP AT TIME ZONE 'UTC') NOT NULL,
    metadata text,
    CONSTRAINT objects_in_canonical_order CHECK ((type1, id1) < (type2, id2)),
    PRIMARY KEY (type1, id1, type2, id2)
);

CREATE UNIQUE INDEX xref__inverse__key ON XRef(type2, id2, type1, id1);
CREATE UNIQUE INDEX xref__int__key ON XRef(type1, id1_int, type2, id2_int);
CREATE UNIQUE INDEX xref__int_inverse__key ON XRef(type2, id2_int, type1, id1_int);
CREATE INDEX xref__type1__type2__idx ON XRef(type1, type2);

CREATE INDEX xref__creator__idx ON XRef(creator);

INSERT INTO LaunchpadDatabaseRevision VALUES (2209, 70, 0);
