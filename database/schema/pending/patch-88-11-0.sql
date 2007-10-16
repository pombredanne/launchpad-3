SET client_min_messages=ERROR;

CREATE TABLE StructuralSubscription (
  id serial PRIMARY KEY,

  product integer REFERENCES Product,
  productseries integer REFERENCES ProductSeries,
  project integer REFERENCES Project,
  milestone integer REFERENCES Milestone,
  distribution integer REFERENCES Distribution,
  distrorelease integer REFERENCES DistroRelease,
  sourcepackagerelease integer REFERENCES SourcePackageRelease,
  binarypackagerelease integer REFERENCES BinaryPackageRelease,

  subscriber integer NOT NULL REFERENCES Person,
  subscribed_by integer NOT NULL REFERENCES Person,

  specification_flavour integer,
  -- value from enum SpecificationStructuralSubscriptionFlavour
  bug_flavour integer,
  -- value from enum BugStructuralSubscriptionFlavour
  translation_flavour integer,
  -- value from enum TranslationStructuralSubscriptionFlavour
  code_flavour integer,
  -- value from enum CodeStructuralSubscriptionFlavour
  registry_flavour integer,
  -- value from enum RegistryStructuralSubscriptionFlavour

  is_verbose boolean, -- send full context or only the latest change

  date_created timestamp without time zone NOT NULL
    DEFAULT (CURRENT_TIMESTAMP AT TIME ZONE 'UTC'),

  CONSTRAINT structural_subscription_one_target CHECK (
    (product IS NOT NULL AND productseries IS NULL AND
     project IS NULL AND milestone IS NULL AND
     distribution IS NULL AND distrorelease IS NULL AND
     sourcepackagerelease IS NULL AND binarypackagerelease IS NULL) OR
    (product IS NULL AND productseries IS NOT NULL AND
     project IS NULL AND milestone IS NULL AND
     distribution IS NULL AND distrorelease IS NULL AND
     sourcepackagerelease IS NULL AND binarypackagerelease IS NULL) OR
    (product IS NULL AND productseries IS NULL AND
     project IS NOT NULL AND milestone IS NULL AND
     distribution IS NULL AND distrorelease IS NULL AND
     sourcepackagerelease IS NULL AND binarypackagerelease IS NULL) OR
    (product IS NULL AND productseries IS NULL AND
     project IS NULL AND milestone IS NOT NULL AND
     distribution IS NULL AND distrorelease IS NULL AND
     sourcepackagerelease IS NULL AND binarypackagerelease IS NULL) OR
    (product IS NULL AND productseries IS NULL AND
     project IS NULL AND milestone IS NULL AND
     distribution IS NOT NULL AND distrorelease IS NULL AND
     sourcepackagerelease IS NULL AND binarypackagerelease IS NULL) OR
    (product IS NULL AND productseries IS NULL AND
     project IS NULL AND milestone IS NULL AND
     distribution IS NULL AND distrorelease IS NOT NULL AND
     sourcepackagerelease IS NULL AND binarypackagerelease IS NULL) OR
    (product IS NULL AND productseries IS NULL AND
     project IS NULL AND milestone IS NULL AND
     distribution IS NULL AND distrorelease IS NULL AND
     sourcepackagerelease IS NOT NULL AND binarypackagerelease IS NULL) OR
    (product IS NULL AND productseries IS NULL AND
     project IS NULL AND milestone IS NULL AND
     distribution IS NULL AND distrorelease IS NULL AND
     sourcepackagerelease IS NULL AND binarypackagerelease IS NOT NULL))
);

CREATE TABLE Notification (
  id serial PRIMARY KEY,

  bug integer REFERENCES Bug,
  specification integer REFERENCES Specification,
  branch integer REFERENCES branch,
  translationgroup integer REFERENCES TranslationGroup,
  question integer REFERENCES Question,
  
  message integer NOT NULL REFERENCES Message,
  date_emailed timestamp,

  structuralsubscription integer REFERENCES StructuralSubscription,
  bugsubscription integer REFERENCES BugSubscription,
  questionsubscription integer REFERENCES QuestionSubscription,
  specificationsubscription integer REFERENCES SpecificationSubscription,
  posubscription integer REFERENCES POSubscription,

  CONSTRAINT notification_one_or_no_application CHECK (
     -- A notification can have no application linked
     -- (a registry change, for example)
    (bug IS NULL AND specification IS NULL AND branch IS NULL AND
     translationgroup IS NULL AND question IS NULL) OR
     -- At the most, a notification can have one application linked
    (bug IS NOT NULL AND specification IS NULL AND branch IS NULL AND
     translationgroup IS NULL AND question IS NULL) OR
    (bug IS NULL AND specification IS NOT NULL AND branch IS NULL AND
     translationgroup IS NULL AND question IS NULL) OR
    (bug IS NULL AND specification IS NULL AND branch IS NOT NULL AND
     translationgroup IS NULL AND question IS NULL) OR
    (bug IS NULL AND specification IS NULL AND branch IS NULL AND
     translationgroup IS NOT NULL AND question IS NULL) OR
    (bug IS NULL AND specification IS NULL AND branch IS NULL AND
     translationgroup IS NULL AND question IS NOT NULL)),

  CONSTRAINT notification_one_subscription CHECK (
    (structuralsubscription IS NOT NULL AND bugsubscription IS NULL AND
     questionsubscription IS NULL AND specificationsubscription IS NULL AND
     posubscription IS NULL) OR
    (structuralsubscription IS NULL AND bugsubscription IS NOT NULL AND
     questionsubscription IS NULL AND specificationsubscription IS NULL AND
     posubscription IS NULL) OR
    (structuralsubscription IS NULL AND bugsubscription IS NULL AND
     questionsubscription IS NOT NULL AND specificationsubscription IS NULL AND
     posubscription IS NULL) OR
    (structuralsubscription IS NULL AND bugsubscription IS NULL AND
     questionsubscription IS NULL AND specificationsubscription IS NOT NULL AND
     posubscription IS NULL) OR
    (structuralsubscription IS NULL AND bugsubscription IS NULL AND
     questionsubscription IS NULL AND specificationsubscription IS NULL AND
     posubscription IS NOT NULL))
);

INSERT INTO LaunchpadDatabaseRevision VALUES (88, 11, 0);

