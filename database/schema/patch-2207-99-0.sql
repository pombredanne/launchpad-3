-- Copyright 2010 Canonical Ltd.  This software is licensed under the
-- GNU Affero General Public License version 3 (see the file LICENSE).

SET client_min_messages=ERROR;

CREATE TABLE BugSubscriptionFilter (
    id serial PRIMARY KEY,
    bugsubscription integer REFERENCES BugSubscription(id),
    structuralsubscription integer REFERENCES StructuralSubscription(id),
    assignee integer REFERENCES Person(id),
    unassigned boolean NOT NULL,
    reporter integer REFERENCES Person(id),
    supervisor integer REFERENCES Person(id),
    commenter integer REFERENCES Person(id),
    subscriber integer REFERENCES Person(id),
    find_all_tags boolean NOT NULL,
    include_any_tags boolean NOT NULL,
    exclude_any_tags boolean NOT NULL,
    has_cve boolean NOT NULL,
    bugs_affecting_me boolean NOT NULL,
    bugs_with_patches boolean NOT NULL,
    bugs_with_branches boolean,
    hide_duplicate_bugs boolean NOT NULL,
    fulltext_search tsquery,
    description text,

    CONSTRAINT bugsubscriptionfilter__exactly_one_target CHECK
        ((bugsubscription IS NULL AND structuralsubscription IS NOT NULL) OR
         (bugsubscription IS NOT NULL AND structuralsubscription IS NULL))
);

CREATE INDEX bugsubscriptionfilter__bugsubscription
    ON BugSubscriptionFilter(bugsubscription);
CREATE INDEX bugsubscriptionfilter__structuralsubscription
    ON BugSubscriptionFilter(structuralsubscription);

CREATE TABLE BugSubscriptionFilterStatus (
    id serial PRIMARY KEY,
    filter integer REFERENCES BugSubscriptionFilter(id) NOT NULL,
    status integer NOT NULL);

CREATE INDEX bugsubscriptionfilterstatus__filter
    ON BugSubscriptionFilterStatus(filter);

CREATE TABLE BugSubscriptionFilterImportance (
    id serial PRIMARY KEY,
    filter integer REFERENCES BugSubscriptionFilter(id) NOT NULL,
    importance integer NOT NULL);

CREATE INDEX bugsubscriptionfilterimportance__filter
    ON BugSubscriptionFilterImportance(filter);

CREATE TABLE BugSubscriptionFilterMilestone (
    id serial PRIMARY KEY,
    filter integer REFERENCES BugSubscriptionFilter(id) NOT NULL,
    milestone integer REFERENCES milestone(id) NOT NULL);

CREATE INDEX bugsubscriptionfiltermilestone__filter
    ON BugSubscriptionFilterMilestone(filter);

CREATE TABLE BugSubscriptionFilterTag (
    id serial PRIMARY KEY,
    filter integer REFERENCES BugSubscriptionFilter(id) NOT NULL,
    tag text NOT NULL,
    include boolean NOT NULL);

CREATE INDEX bugsubscriptionfiltertag__filter
    ON BugSubscriptionFilterTag(filter);
CREATE INDEX bugsubscriptionfiltertag__tag
    ON BugSubscriptionFilterTag(tag);

CREATE TABLE BugSubscriptionFilterComponent (
    id serial PRIMARY KEY,
    filter integer REFERENCES BugSubscriptionFilter(id) NOT NULL,
    component integer REFERENCES Component(id) NOT NULL);

CREATE INDEX bugsubscriptionfiltercomponent__filter
    ON BugSubscriptionFilterComponent(filter);

CREATE TABLE BugSubscriptionFilterUpstreamStatus (
    id serial PRIMARY KEY,
    filter integer REFERENCES BugSubscriptionFilter(id) NOT NULL,
    status integer NOT NULL);

CREATE INDEX bugsubscriptionfilterupstreamstatus__filter
    ON BugSubscriptionFilterUpstreamStatus(filter);

INSERT INTO LaunchpadDatabaseRevision VALUES (2207, 99, 0);
