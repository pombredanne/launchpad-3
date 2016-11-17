-- Copyright 2016 Canonical Ltd.  This software is licensed under the
-- GNU Affero General Public License version 3 (see the file LICENSE).

SET client_min_messages=ERROR;

ALTER TABLE GitSubscription ADD COLUMN paths text;

COMMENT ON COLUMN GitSubscription.paths IS 'A JSON-encoded list of patterns matching subscribed reference paths.';

INSERT INTO LaunchpadDatabaseRevision VALUES (2209, 61, 9);
