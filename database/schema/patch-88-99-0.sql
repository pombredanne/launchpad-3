SET client_min_messages=ERROR;

CREATE TABLE StructuralSubscription (
  id serial PRIMARY KEY,

  product integer REFERENCES Product,
  productseries integer REFERENCES ProductSeries,
  project integer REFERENCES Project,
  milestone integer REFERENCES Milestone,
  distribution integer REFERENCES Distribution,
  distroseries integer REFERENCES DistroSeries,
  sourcepackagename integer REFERENCES SourcePackageName,

  subscriber integer NOT NULL REFERENCES Person,
  subscribed_by integer NOT NULL REFERENCES Person,

  bug_notification_level integer NOT NULL,
  -- value from enum BugNotificationLevel
  blueprint_notification_level integer NOT NULL,
  -- value from enum BlueprintNotificationLevel

  date_created timestamp without time zone NOT NULL
    DEFAULT (CURRENT_TIMESTAMP AT TIME ZONE 'UTC'),
  date_last_updated timestamp without time zone NOT NULL
    DEFAULT (CURRENT_TIMESTAMP AT TIME ZONE 'UTC'),

  CONSTRAINT structural_subscription_one_target CHECK (
    (product IS NOT NULL AND productseries IS NULL AND
     project IS NULL AND milestone IS NULL AND
     distribution IS NULL AND distroseries IS NULL AND
     sourcepackagename IS NULL) OR
    (product IS NULL AND productseries IS NOT NULL AND
     project IS NULL AND milestone IS NULL AND
     distribution IS NULL AND distroseries IS NULL AND
     sourcepackagename IS NULL) OR
    (product IS NULL AND productseries IS NULL AND
     project IS NOT NULL AND milestone IS NULL AND
     distribution IS NULL AND distroseries IS NULL AND
     sourcepackagename IS NULL) OR
    (product IS NULL AND productseries IS NULL AND
     project IS NULL AND milestone IS NOT NULL AND
     distribution IS NULL AND distroseries IS NULL AND
     sourcepackagename IS NULL) OR
    (product IS NULL AND productseries IS NULL AND
     project IS NULL AND milestone IS NULL AND
     distribution IS NOT NULL AND distroseries IS NULL AND
     sourcepackagename IS NULL) OR
    (product IS NULL AND productseries IS NULL AND
     project IS NULL AND milestone IS NULL AND
     distribution IS NULL AND distroseries IS NOT NULL AND
     sourcepackagename IS NULL) OR
     /* Subscription to (distribution, sourcepackagename) */
    (product IS NULL AND productseries IS NULL AND
     project IS NULL AND milestone IS NULL AND
     distribution IS NOT NULL AND distroseries IS NULL AND
     sourcepackagename IS NOT NULL))
);

INSERT INTO LaunchpadDatabaseRevision VALUES (88, 99, 0);