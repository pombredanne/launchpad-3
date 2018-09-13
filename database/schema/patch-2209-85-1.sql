-- Copyright 2018 Canonical Ltd.  This software is licensed under the
-- GNU Affero General Public License version 3 (see the file LICENSE).

SET client_min_messages=ERROR;

CREATE TABLE GitActivity (
    id serial PRIMARY KEY,
    repository integer NOT NULL REFERENCES gitrepository,
    date_changed timestamp without time zone DEFAULT (CURRENT_TIMESTAMP AT TIME ZONE 'UTC') NOT NULL,
    changer integer NOT NULL REFERENCES person,
    changee integer REFERENCES person,
    what_changed integer NOT NULL,
    old_value text,
    new_value text
);

CREATE INDEX gitactivity__repository__date_changed__id__idx
    ON GitActivity(repository, date_changed DESC, id DESC);

COMMENT ON TABLE GitActivity IS 'An activity log entry for a Git repository.';
COMMENT ON COLUMN GitActivity.repository IS 'The repository that this log entry is for.';
COMMENT ON COLUMN GitActivity.date_changed IS 'The time when this change happened.';
COMMENT ON COLUMN GitActivity.changer IS 'The user who made this change.';
COMMENT ON COLUMN GitActivity.changee IS 'The person or team that this change was applied to.';
COMMENT ON COLUMN GitActivity.what_changed IS 'The property of the repository that changed.';
COMMENT ON COLUMN GitActivity.old_value IS 'The value before the change.';
COMMENT ON COLUMN GitActivity.new_value IS 'The value after the change.';

INSERT INTO LaunchpadDatabaseRevision VALUES (2209, 85, 1);
