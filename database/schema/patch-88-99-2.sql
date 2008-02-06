SET client_min_messages=ERROR;

INSERT INTO StructuralSubscription (
  product,
  subscriber, subscribed_by,
  bug_notification_level, blueprint_notification_level)
SELECT id,
       bugcontact, bugcontact,
       40, 10
FROM Product
WHERE bugcontact IS NOT NULL;

INSERT INTO LaunchpadDatabaseRevision VALUES (88, 99, 2);
