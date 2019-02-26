-- Copyright 2016 Canonical Ltd.  This software is licensed under the
-- GNU Affero General Public License version 3 (see the file LICENSE).

SET client_min_messages=ERROR;

ALTER TABLE Webhook ADD COLUMN snap integer REFERENCES Snap;

ALTER TABLE Webhook DROP CONSTRAINT one_target;
ALTER TABLE Webhook ADD CONSTRAINT one_target CHECK (null_count(ARRAY[git_repository, branch, snap]) = 2);

CREATE INDEX webhook__snap__id__idx
    ON webhook(snap, id) WHERE snap IS NOT NULL;

INSERT INTO LaunchpadDatabaseRevision VALUES (2209, 69, 2);
