-- Copyright 2011 Canonical Ltd.  This software is licensed under the
-- GNU Affero General Public License version 3 (see the file LICENSE).

SET client_min_messages=ERROR;

CREATE TABLE milestonetag (
    id integer NOT NULL PRIMARY KEY,
    milestone integer REFERENCES milestone ON DELETE CASCADE,
    tag text NOT NULL,
    CONSTRAINT valid_tag CHECK (valid_name(tag))
);

ALTER TABLE ONLY milestonetag
    ADD CONSTRAINT milestonetag__tag__milestone__key UNIQUE (tag, milestone);

CREATE INDEX milestonetag__milestones_idx ON milestonetag USING btree (milestone);
CREATE INDEX milestonetag__tags_idx ON milestonetag (tag);

INSERT INTO LaunchpadDatabaseRevision VALUES (2209, 0, 3);
