-- Copyright 2015 Canonical Ltd.  This software is licensed under the
-- GNU Affero General Public License version 3 (see the file LICENSE).

SET client_min_messages=ERROR;

ALTER TABLE Webhook ADD COLUMN branch integer REFERENCES Branch;

ALTER TABLE Webhook DROP CONSTRAINT webhook_git_repository_check;
ALTER TABLE Webhook ADD CONSTRAINT one_target CHECK ((git_repository IS NOT NULL) != (branch IS NOT NULL));

CREATE INDEX webhook__branch__id__idx
    ON webhook(branch, id) WHERE branch IS NOT NULL;

INSERT INTO LaunchpadDatabaseRevision VALUES (2209, 66, 1);
