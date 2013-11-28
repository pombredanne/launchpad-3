-- Copyright 2013 Canonical Ltd.  This software is licensed under the
-- GNU Affero General Public License version 3 (see the file LICENSE).

SET client_min_messages=ERROR;

ALTER TABLE builder ALTER COLUMN processor DROP NOT NULL;

CREATE TABLE builderprocessor (
    builder integer NOT NULL REFERENCES builder,
    processor integer NOT NULL REFERENCES processor,
    PRIMARY KEY (builder, processor)
);
CREATE INDEX builderprocessor__processor__idx ON builderprocessor(processor);

INSERT INTO builderprocessor (builder, processor)
    SELECT id, processor FROM builder;

INSERT INTO LaunchpadDatabaseRevision VALUES (2209, 52, 0);
