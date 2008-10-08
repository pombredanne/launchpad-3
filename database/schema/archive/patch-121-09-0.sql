SET client_min_messages=ERROR;

INSERT INTO StructuralSubscription (
 distribution, sourcepackagename,
 subscriber, subscribed_by,
 bug_notification_level, blueprint_notification_level)
SELECT distribution, sourcepackagename,
      bugcontact, bugcontact,
      40, 10
FROM PackageBugContact;

TRUNCATE PackageBugContact;

INSERT INTO StructuralSubscription (
  product,
  subscriber, subscribed_by,
  bug_notification_level, blueprint_notification_level)
SELECT id,
       bugcontact, bugcontact,
       40, 10
FROM Product
WHERE bugcontact IS NOT NULL;

INSERT INTO LaunchpadDatabaseRevision VALUES (121, 9, 0);
