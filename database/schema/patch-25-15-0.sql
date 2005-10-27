set client_min_messages=ERROR;

/* the core specification table */ 

CREATE TABLE Specification (
  id             serial PRIMARY KEY,
  name           text NOT NULL CONSTRAINT valid_name CHECK (valid_name(name)),
  title          text NOT NULL,
  summary        text,
  owner          integer NOT NULL,
  assignee       integer,
  drafter        integer,
  approver       integer,
  datecreated    timestamp WITHOUT TIME ZONE NOT NULL
                           DEFAULT (CURRENT_TIMESTAMP AT TIME ZONE 'UTC'),
  product        integer,
  productseries  integer,
  distribution   integer,
  distrorelease  integer,
  milestone      integer,
  status         integer NOT NULL,
  priority       integer NOT NULL,
  specurl        text NOT NULL CONSTRAINT valid_url
                    CHECK (valid_absolute_url(specurl)),
  whiteboard     text
);

ALTER TABLE Specification ADD CONSTRAINT
    specification_owner_fk FOREIGN KEY (owner) REFERENCES Person(id);

ALTER TABLE Specification ADD CONSTRAINT
    specification_assignee_fk FOREIGN KEY (assignee) REFERENCES Person(id);

ALTER TABLE Specification ADD CONSTRAINT
    specification_drafter_fk FOREIGN KEY (drafter) REFERENCES Person(id);

ALTER TABLE Specification ADD CONSTRAINT
    specification_approver_fk FOREIGN KEY (approver) REFERENCES Person(id);

-- Specification must be linked to either a production or a distribution
ALTER TABLE Specification ADD CONSTRAINT product_xor_distribution
    CHECK (product IS NULL <> distribution IS NULL);

-- Specification name is UNIQUE in the context of a product or distribution
ALTER TABLE Specification ADD CONSTRAINT
    specification_product_name_uniq UNIQUE (name, product);

ALTER TABLE Specification ADD CONSTRAINT
    specification_distribution_name_uniq UNIQUE (distribution, name);

ALTER TABLE Specification ADD CONSTRAINT
    specification_distribution_fk FOREIGN KEY (distribution)
    REFERENCES Distribution(id);

ALTER TABLE Specification ADD CONSTRAINT distribution_and_distrorelease
    CHECK (distrorelease IS NULL OR distribution IS NOT NULL);

ALTER TABLE DistroRelease ADD CONSTRAINT
    distrorelease_distro_release_unique UNIQUE (distribution, id);

ALTER TABLE Specification ADD CONSTRAINT
    specification_distrorelease_valid
    FOREIGN KEY (distribution, distrorelease)
    REFERENCES DistroRelease(distribution, id);

ALTER TABLE Specification ADD CONSTRAINT
    specification_product_fk FOREIGN KEY (product) REFERENCES Product(id);

ALTER TABLE Specification ADD CONSTRAINT product_and_productseries
    CHECK (productseries IS NULL OR product IS NOT NULL);

ALTER TABLE ProductSeries ADD CONSTRAINT
    productseries_product_series_uniq UNIQUE (product, id);

ALTER TABLE Specification ADD CONSTRAINT
    specification_productseries_valid FOREIGN KEY (product, productseries)
    REFERENCES ProductSeries(product, id);

-- milestone should reference a valid Milestone for the product or distribution
ALTER TABLE Specification ADD CONSTRAINT
    specification_product_milestone_fk FOREIGN KEY (product, milestone)
    REFERENCES Milestone(product, id);

ALTER TABLE Specification ADD CONSTRAINT
    specification_distribution_milestone_fk
    FOREIGN KEY (distribution, milestone)
    REFERENCES Milestone(distribution, id);

ALTER TABLE Specification ADD CONSTRAINT
    specification_specurl_uniq UNIQUE (specurl);


 /* Link specs and bugs */

CREATE TABLE SpecificationBug (
    id            serial PRIMARY KEY,
    specification integer NOT NULL,
    bug           integer NOT NULL
);

ALTER TABLE SpecificationBug ADD CONSTRAINT
    specificationbug_specification_fk FOREIGN KEY (specification)
    REFERENCES Specification(id);

ALTER TABLE SpecificationBug ADD CONSTRAINT
    specificationbug_bug_fk FOREIGN KEY (bug)
    REFERENCES Bug(id);

ALTER TABLE SpecificationBug ADD CONSTRAINT
    specification_bug_uniq UNIQUE (specification, bug);

CREATE INDEX specificationbug_specification_idx
    ON SpecificationBug(specification);

CREATE INDEX specificationbug_bug_idx
    ON Specificationbug(bug);

/* Allow for subscriptions to specifications */

CREATE TABLE SpecificationSubscription (
    id            serial PRIMARY KEY,
    specification integer NOT NULL,
    person        integer NOT NULL
);

ALTER TABLE SpecificationSubscription ADD CONSTRAINT
    specificationsubscription_specification_fk FOREIGN KEY (specification)
    REFERENCES Specification(id);

ALTER TABLE SpecificationSubscription ADD CONSTRAINT
    specificationsubscription_person_fk FOREIGN KEY (person)
    REFERENCES Person(id);

ALTER TABLE SpecificationSubscription ADD CONSTRAINT
    specificationsubscription_spec_person_uniq
    UNIQUE (specification, person);

CREATE INDEX specificationsubscription_subscriber_idx
    ON SpecificationSubscription(person);


/* Allow for Specification Dependencies */

CREATE TABLE SpecificationDependency (
    id                serial PRIMARY KEY,
    specification     integer NOT NULL,
    dependency        integer NOT NULL
);

ALTER TABLE SpecificationDependency ADD CONSTRAINT
    specificationdependency_specification_fk FOREIGN KEY (specification)
    REFERENCES Specification(id);

ALTER TABLE SpecificationDependency ADD CONSTRAINT
    specificationdependency_dependency_fk FOREIGN KEY (dependency)
    REFERENCES Specification(id);

ALTER TABLE SpecificationDependency ADD CONSTRAINT
    specificationdependency_not_self CHECK (specification <> dependency);

ALTER TABLE SpecificationDependency ADD CONSTRAINT
    specificationdependency_uniq UNIQUE (specification, dependency);

CREATE INDEX specificationdependency_specification_idx
    ON SpecificationDependency(specification);

CREATE INDEX specificationdependency_dependency_idx
    ON SpecificationDependency(dependency);


/* Create queues for subscription reviews */

CREATE TABLE SpecificationReview (
    id                serial PRIMARY KEY,
    specification     integer NOT NULL,
    reviewer          integer NOT NULL,
    requestor         integer NOT NULL,
    queuemsg          text
);

ALTER TABLE SpecificationReview ADD CONSTRAINT
    specificationreview_specification_fk FOREIGN KEY (specification)
    REFERENCES Specification(id);

ALTER TABLE SpecificationReview ADD CONSTRAINT
    specificationreview_reviewer_fk FOREIGN KEY (reviewer)
    REFERENCES Person(id);

ALTER TABLE SpecificationReview ADD CONSTRAINT
    specificationreview_requestor_fk FOREIGN KEY (requestor)
    REFERENCES Person(id);

ALTER TABLE SpecificationReview ADD CONSTRAINT
    specificationreview_spec_reviewer_uniq
    UNIQUE (specification, reviewer);

CREATE INDEX specificationreview_specification_idx ON
    SpecificationReview(specification);

CREATE INDEX specificationreview_reviewer_idx ON
    SpecificationReview(reviewer);


/* fix up old fk name */

ALTER TABLE ProductSeries DROP CONSTRAINT "$1";
ALTER TABLE ProductSeries ADD CONSTRAINT productseries_product_fk
    FOREIGN KEY (product) REFERENCES Product;

/* Improve Bounty query performance */

CREATE INDEX bounty_usdvalue_idx ON Bounty(usdvalue);

INSERT INTO LaunchpadDatabaseRevision VALUES (25,15,0);


