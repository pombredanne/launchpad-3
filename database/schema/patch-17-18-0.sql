
SET client_min_messages = error;

-- unrelated to translationsightings, but since we have a big db patch
-- anyway... i would like to have datecreated on most substantial
-- content items, so we can produce quick lists of how many new people
-- joined this week etc

-- nuke the POTemplate title, we will use a generated one

ALTER TABLE POTemplate DROP COLUMN title;

-- now, make sure we can ask the user who uploads a pofile if it is the
-- published one, and remember the answer

ALTER TABLE POFile ADD COLUMN rawfilepublished boolean;

ALTER TABLE Person ADD COLUMN datecreated timestamp without time zone;
ALTER TABLE Person ALTER COLUMN datecreated
    SET DEFAULT CURRENT_TIMESTAMP AT TIME ZONE 'UTC';
UPDATE Person SET datecreated=DEFAULT WHERE datecreated IS NULL;
ALTER TABLE Person ALTER COLUMN datecreated SET NOT NULL;

CREATE INDEX person_datecreated_idx ON Person(datecreated);

ALTER TABLE ProductSeries ADD COLUMN datecreated timestamp without time zone;
ALTER TABLE ProductSeries ALTER COLUMN datecreated
    SET DEFAULT CURRENT_TIMESTAMP AT TIME ZONE 'UTC';
UPDATE ProductSeries SET datecreated=DEFAULT WHERE datecreated IS NULL;
ALTER TABLE ProductSeries ALTER COLUMN datecreated SET NOT NULL;

CREATE INDEX productseries_datecreated_idx ON ProductSeries(datecreated);

ALTER TABLE ProductRelease ADD COLUMN datecreated timestamp without time zone;
ALTER TABLE ProductRelease ALTER COLUMN datecreated
    SET DEFAULT CURRENT_TIMESTAMP AT TIME ZONE 'UTC';
UPDATE ProductRelease SET datecreated=DEFAULT WHERE datecreated IS NULL;
ALTER TABLE ProductRelease ALTER COLUMN datecreated SET NOT NULL;

CREATE INDEX productrelease_datecreated_idx ON ProductRelease(datecreated);

ALTER TABLE POFile ADD COLUMN datecreated timestamp without time zone;
ALTER TABLE POFile ALTER COLUMN datecreated
    SET DEFAULT CURRENT_TIMESTAMP AT TIME ZONE 'UTC';
UPDATE POFile SET datecreated=DEFAULT WHERE datecreated IS NULL;
ALTER TABLE POFile ALTER COLUMN datecreated SET NOT NULL;

CREATE INDEX pofile_datecreated_idx ON POFile(datecreated);

-- general indexation for performance
CREATE INDEX archarchive_owner_idx ON ArchArchive(owner);

CREATE INDEX person_teamowner_idx ON Person(teamowner);
CREATE INDEX person_karma_idx ON Person(karma);

CREATE INDEX bug_duplicateof_idx ON Bug(duplicateof);

CREATE INDEX bugactivity_datechanged_idx ON BugActivity(datechanged);
CREATE INDEX bugactivity_bug_datechanged_idx ON
    BugActivity(bug, datechanged);
CREATE INDEX bugactivity_person_datechanged_idx ON
    BugActivity(person, datechanged);

CREATE INDEX bugexternalref_bug_idx ON BugExternalRef(bug);
CREATE INDEX bugexternalref_datecreated_idx ON BugExternalRef(datecreated);

CREATE INDEX bugmessage_bug_idx ON BugMessage(bug);
CREATE INDEX bugmessage_message_idx ON BugMessage(message);

CREATE INDEX bugsubscription_bug_idx ON BugSubscription(bug);
CREATE INDEX bugsubscription_person_idx ON BugSubscription(person);

CREATE INDEX bugtask_distribution_and_sourcepackagename_idx ON
    BugTask(distribution, sourcepackagename);
CREATE INDEX bugtask_distrorelease_and_sourcepackagename_idx ON
    BugTask(distrorelease, sourcepackagename);
CREATE INDEX bugtask_datecreated_idx ON BugTask(datecreated);

CREATE INDEX bugtracker_owner_idx ON BugTracker(owner);

CREATE INDEX bugwatch_bug_idx ON BugWatch(bug);
CREATE INDEX bugwatch_bugtracker_idx ON BugWatch(bugtracker);
CREATE INDEX bugwatch_owner_idx ON BugWatch(owner);
CREATE INDEX bugwatch_datecreated_idx ON BugWatch(datecreated);

CREATE INDEX build_datecreated_idx ON Build(datecreated);
CREATE INDEX build_datebuilt_idx ON Build(datebuilt);
CREATE INDEX build_builder_and_buildstate_idx ON Build(builder, buildstate);
CREATE INDEX build_distroarchrelease_and_datebuilt_idx ON
    Build(distroarchrelease, datebuilt);
CREATE INDEX build_distroarchrelease_and_buildstate_idx ON
    Build(distroarchrelease, buildstate);
CREATE INDEX build_buildstate_idx ON Build(buildstate);

CREATE INDEX changeset_datecreated_idx ON Changeset(datecreated);
CREATE INDEX changeset_branch_and_name_idx ON Changeset(branch, name);

ALTER TABLE ManifestEntry DROP CONSTRAINT "$6";
ALTER TABLE ManifestEntry ADD CONSTRAINT manifestentry_changeset_fk
    FOREIGN KEY (branch, changeset) REFERENCES ChangeSet(branch, id);
ALTER TABLE ManifestEntry DROP CONSTRAINT "$4";
ALTER TABLE ManifestEntry ADD CONSTRAINT manifestentry_branch_fk
    FOREIGN KEY (branch) REFERENCES Branch(id);

ALTER TABLE Country ADD CONSTRAINT country_name_uniq UNIQUE (name);
ALTER TABLE Country ADD CONSTRAINT country_code2_uniq UNIQUE (iso3166code2);
ALTER TABLE Country ADD CONSTRAINT country_code3_uniq UNIQUE (iso3166code3);

CREATE INDEX cveref_bug_idx ON CVERef(bug);
CREATE INDEX cveref_datecreated_idx ON CVERef(datecreated);

CREATE INDEX distribution_translationgroup_idx ON
    Distribution(translationgroup);

CREATE INDEX product_translationgroup_idx ON Product(translationgroup);
CREATE INDEX project_translationgroup_idx ON Project(translationgroup);

CREATE INDEX distrobounty_distribution_idx ON DistroBounty(distribution);

CREATE INDEX message_owner_idx ON Message(owner);
CREATE INDEX message_parent_idx ON Message(parent);

CREATE INDEX packaging_sourcepackagename_idx ON Packaging(sourcepackagename);
CREATE INDEX packaging_distrorelease_and_sourcepackagename_idx ON
    Packaging(distrorelease, sourcepackagename);

ANALYSE;

INSERT INTO LaunchpadDatabaseRevision VALUES (17, 18, 0);
