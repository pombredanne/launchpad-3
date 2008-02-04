SET client_min_messages=ERROR;

INSERT INTO StructuralSubscription (
  distribution, sourcepackagename,
  subscriber, subscribed_by,
  bug_notification_level, blueprint_notification_level)
SELECT distribution, sourcepackagename,
       bugcontact, bugcontact,
       40, 10
FROM PackageBugContact;

DELETE FROM PackageBugContact WHERE TRUE;

INSERT INTO LaunchpadDatabaseRevision VALUES (88, 99, 0);
