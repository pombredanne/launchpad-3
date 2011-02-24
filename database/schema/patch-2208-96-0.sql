-- Copyright 2011 Canonical Ltd.  This software is licensed under the
-- GNU Affero General Public License version 3 (see the file LICENSE).
SET client_min_messages=ERROR;

CREATE TABLE BugNotificationFilter (
    id SERIAL        PRIMARY KEY,
    bug_notification INTEGER NOT NULL REFERENCES BugNotification(id),
    bug_subscription_filter
                     INTEGER NOT NULL REFERENCES BugSubscriptionFilter(id)
);

CREATE INDEX BugNotificationFilter__bug_notification__idx ON
  BugNotificationFilter(bug_notification);

CREATE INDEX BugNotificationFilter__bug_subscription_filter__idx ON
  BugNotificationFilter(bug_subscription_filter);

INSERT INTO LaunchpadDatabaseRevision VALUES (2208, 96, 0);
