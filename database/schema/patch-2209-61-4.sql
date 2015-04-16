-- Copyright 2015 Canonical Ltd.  This software is licensed under the
-- GNU Affero General Public License version 3 (see the file LICENSE).

SET client_min_messages=ERROR;

CREATE TABLE GitSubscription (
    id serial PRIMARY KEY,
    person integer NOT NULL REFERENCES person,
    repository integer NOT NULL REFERENCES gitrepository,
    date_created timestamp without time zone DEFAULT (CURRENT_TIMESTAMP AT TIME ZONE 'UTC') NOT NULL,
    notification_level integer DEFAULT 1 NOT NULL,
    max_diff_lines integer,
    review_level integer DEFAULT 0 NOT NULL,
    subscribed_by integer NOT NULL REFERENCES person
);

CREATE INDEX gitsubscription__repository__idx
    ON GitSubscription(repository);
CREATE INDEX gitsubscription__subscribed_by__idx
    ON GitSubscription(subscribed_by);
CREATE UNIQUE INDEX gitsubscription__person__repository__key
    ON GitSubscription(person, repository);

COMMENT ON TABLE GitSubscription IS 'An association between a person or team and a Git repository.';
COMMENT ON COLUMN GitSubscription.person IS 'The person or team associated with the repository.';
COMMENT ON COLUMN GitSubscription.repository IS 'The repository associated with the person or team.';
COMMENT ON COLUMN GitSubscription.notification_level IS 'The level of email the person wants to receive from repository updates.';
COMMENT ON COLUMN GitSubscription.max_diff_lines IS 'If the generated diff for a revision is larger than this number, then the diff is not sent in the notification email.';
COMMENT ON COLUMN GitSubscription.review_level IS 'The level of email the person wants to receive from review activity.';
COMMENT ON COLUMN GitSubscription.subscribed_by IS 'The person who created this subscription.';

INSERT INTO LaunchpadDatabaseRevision VALUES (2209, 61, 4);
