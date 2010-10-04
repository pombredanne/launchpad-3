-- Copyright 2010 Canonical Ltd.  This software is licensed under the
-- GNU Affero General Public License version 3 (see the file LICENSE).
SET client_min_messages=ERROR;

CREATE TABLE BranchMergeQueue (
    id serial NOT NULL PRIMARY KEY,
    registrant integer NOT NULL REFERENCES Person,
    owner integer NOT NULL REFERENCES Person,
    name TEXT NOT NULL,
    description TEXT,
    configuration TEXT,
    date_created timestamp without time zone
        DEFAULT timezone('UTC'::text, now()) NOT NULL,
    CONSTRAINT owner_name UNIQUE (owner, name)
);

ALTER TABLE Branch DROP COLUMN merge_robot CASCADE;
ALTER TABLE Branch DROP COLUMN merge_control_status;
ALTER TABLE Branch ADD COLUMN merge_queue integer REFERENCES BranchMergeQueue;
ALTER TABLE Branch ADD COLUMN merge_queue_config TEXT;

ALTER TABLE BranchMergeRobot RENAME TO todrop_BranchMergeRobot;

INSERT INTO LaunchpadDatabaseRevision VALUES (2208, 99, 0);
