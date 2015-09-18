-- Copyright 2015 Canonical Ltd.  This software is licensed under the
-- GNU Affero General Public License version 3 (see the file LICENSE).

SET client_min_messages=ERROR;

CREATE TABLE XRef (
    object1_id text NOT NULL,
    object2_id text NOT NULL,
    creator integer REFERENCES Person,
    date_created timestamp without time zone
        DEFAULT (CURRENT_TIMESTAMP AT TIME ZONE 'UTC') NOT NULL,
    metadata text,
    CONSTRAINT objects_in_canonical_order CHECK (object1_id < object2_id),
    PRIMARY KEY (object1_id, object2_id)
);

CREATE UNIQUE INDEX xref__object2_id__object1_id__key
    ON XRef(object2_id, object1_id);

CREATE INDEX xref__creator__idx ON XRef(creator);

INSERT INTO LaunchpadDatabaseRevision VALUES (2209, 70, 0);
