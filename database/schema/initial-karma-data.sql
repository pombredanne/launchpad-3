
set client_min_messages=ERROR;

CREATE TABLE KarmaCategory (
  id                serial PRIMARY KEY,
  name              text NOT NULL,
  title             text NOT NULL,
  summary           text NOT NULL
);


/* let's capture the old dbschema.KarmaActioNCategory data */

INSERT INTO KarmaCategory (id, name, title, summary) VALUES (1, 'misc', 'Miscellaneous', 'This category is a catch-all that is used for karma events that do not fit neatly into any other obvious category.' );
INSERT INTO KarmaCategory (id, name, title, summary) VALUES (2, 'bugs', 'Bug Management', 'This karma category covers work in the Malone bug tracking system, such as filing, closing and otherwise working with bugs.');
INSERT INTO KarmaCategory (id, name, title, summary) VALUES (3, 'translations', 'Translations in Rosetta', 'This categor covers all actions related to translation using the Rosetta web translation portal. Creating new translation projects, submitting new translations and editing existing translations will all earn karma.');
INSERT INTO KarmaCategory (id, name, title, summary) VALUES (4, 'bounties', 'Bounty Tracking', 'This covers all karma associated with the bounty system. Registering bounties, or closing them, will earn you karma.');
INSERT INTO KarmaCategory (id, name, title, summary) VALUES (5, 'registry', 'The Registry', 'This category covers all work with product, projects and the general registry which Launchpad maintains of the open source world.');
INSERT INTO KarmaCategory (id, name, title, summary) VALUES (6, 'specs', 'Specification Tracking', 'This category includes all karma associated with the Launchpad specification tracking system.');
INSERT INTO KarmaCategory (id, name, title, summary) VALUES (7, 'support', 'Support Tracker', 'This is the category for all karma associated with technical support, and the ticket tracker in Launchpad. Help solve users problems to earn this karma.');

/* now all the actions should point at karma categories and we should be 
   able to enforce that in the db */

ALTER TABLE KarmaAction ADD CONSTRAINT karmaaction_category_fk 
    FOREIGN KEY (category) REFERENCES KarmaCategory(id);

/* we need to transition the karmaaction table to use a text name and have a
   title and summary */

ALTER TABLE KarmaAction ADD COLUMN textname text;
ALTER TABLE KarmaAction ADD COLUMN title text;
ALTER TABLE KarmaAction ADD COLUMN summary text;

ALTER TABLE KarmaAction ADD CONSTRAINT karmaaction_name_uniq
    UNIQUE (name);

/* let's capture the old details from dbschema.KarmaActionName */

UPDATE KarmaAction SET textname='bugcreated', title='New Bug Filed', summary='The user filed a new bug report. This is distinct from creating a new "task" for an existing bug, on, say, an upstream product.' WHERE name=1;
UPDATE KarmaAction SET textname='bugcommentadded', title='Bug Comment Added', summary='The user commented on an existing bug in Malone.' WHERE name=2;
UPDATE KarmaAction SET textname='bugtitlechanged', title='Edited Bug Title', summary='The user edited the title of the bug to provide a clearer idea of the core issue.' WHERE name=3;
UPDATE KarmaAction SET textname='bugsummarychanged', title='Edited Bug Summary', summary='The user edited the bug summary. This will specifically help users searching for existing bugs in Malone.' WHERE name=4;
UPDATE KarmaAction SET textname='bugdescriptionchanged', title='Edited Bug Description', summary='The user edited the bug description to describe more clearly the specific symptoms and expected outcomes for the bug. This will also improve the ability of other users to find this bug report and avoid creating duplicates.' WHERE name=5;
UPDATE KarmaAction SET textname='bugextrefadded', title='Bug External Reference Added', summary='The user provided a URL to information which is relevant to this bug, for example, to a mailing list archive where it is discussed, or to a detailed problem report.' WHERE name=6;
UPDATE KarmaAction SET textname='bugcverefadded', title='Bug CVE Link Added', summary='The user has linked a bug report to a specific entry in the CVE database.' WHERE name=7;
UPDATE KarmaAction SET textname='bugfixed', title='Bug Marked as Fixed', summary='The user marked a bug as fixed.' WHERE name=8;
UPDATE  KarmaAction SET textname='bugtaskcreated', title='Bug Task Created', summary='The user has created a new task on a bug. This means that they have indicated that the same bug exists in another place (for example, upstream) and have reported that in Malone.' WHERE name=9;
UPDATE  KarmaAction SET textname='translationtemplateimport', title='Import of Translation Template', summary='The user updated a translation template, providing a newer version to be imported in Rosetta.' WHERE name=10;
UPDATE KarmaAction SET textname='translationimportupstream', title='Upstream Translation Imported', summary='The user imported a set of upstream translations into Rosetta' WHERE name=11;
UPDATE KarmaAction SET textname='translationtemplatedescriptionchanged', title='Edited Translation Template Description', summary='The user updated the description of a specific translation template.' WHERE name=12;
UPDATE KarmaAction SET textname='translationsuggestionadded', title='Translation Suggestion', summary='The user contributed a new suggested translation. That may not yet have been accepted, but is valued nonetheless.' WHERE name=13;
UPDATE KarmaAction SET textname='translationsuggestionapproved', title='Translation Suggestion Approved', summary='The user approved a translation suggestion that was previously contributed by someone else.' WHERE name=14;
UPDATE KarmaAction SET textname='translationreview', title='Translation Review', summary='The user has completed a review of suggested translations.' WHERE name=15;
UPDATE KarmaAction SET textname='bugrejected', title='Bug Rejected', summary='The user has rejected a bug.' WHERE name=16;
UPDATE KarmaAction SET textname='bugaccepted', title='Bug Accepted', summary='The user has marked a bug as accepted.' WHERE name=17;
UPDATE KarmaAction SET textname='bugtaskseveritychanged', title='Bug Severity Changed', summary='The user has updated the severity of a bug task. Note that the severity of a bug can vary depending on where the code is being used, so each bug task has its own severity.' WHERE name=18;
UPDATE KarmaAction SET textname='bugtaskprioritychanged', title='Bug Priority Changed', summary='The user has updated the priority of a particular bug task. Note that bug task has a distinct priority, because each of them will likely have a different developer responsible for them.' WHERE name=19;
UPDATE KarmaAction SET textname='bugmarkedasduplicate', title='Bug Marked as Duplicate', summary='The user has marked a bug as a duplicate of another bug. This greatly reduces the amount of time developers need to spend reviewing existing bug lists.' WHERE name=20;
UPDATE KarmaAction SET textname='bugwatchadded', title='Bug Watch Added', summary ='The user has linked an existing bug in Launchpad to an external bug tracker, to indicate that the bug is being tracked in that bug tracker too.' WHERE name=21;

/* now we can get rid of the old name column and make it the textual one */

ALTER TABLE KarmaAction DROP COLUMN name;
ALTER TABLE KarmaAction RENAME COLUMN textname TO name;

/* and we can make name unique, and all text attributes not null */

ALTER TABLE KarmaAction ALTER COLUMN name SET NOT NULL;
ALTER TABLE KarmaAction ADD CONSTRAINT karmaaction_name_uniq UNIQUE (name);

ALTER TABLE KarmaAction ALTER COLUMN title SET NOT NULL;
ALTER TABLE KarmaAction ALTER COLUMN summary SET NOT NULL;

/* and finally, lets add some new karma actions for the spec system and
   support systems */

INSERT INTO KarmaAction (category, name, points, title, summary) VALUES (6, 'addspec', 30, 'Registered Specification', 'The user has registered a new specification in the Launchpad spec tracker.');
INSERT INTO KarmaAction (category, name, points, title, summary) VALUES (6, 'specpriority', 5, 'Updated Specification Priority', 'The user has changed the priority of a specification to match the requirements of the project.');
INSERT INTO KarmaAction (category, name, points, title, summary) VALUES (6, 'spectitlechanged', 2, 'Edited Specification Title', 'The user edited the title of a specification.');
INSERT INTO KarmaAction (category, name, points, title, summary) VALUES (6, 'specsummarychanged', 2, 'Edited Specification Summary', 'The user edited the summary of a specification.');
INSERT INTO KarmaAction (category, name, points, title, summary) VALUES (6, 'specurlchanged', 2, 'Specification URL Updated', 'The user edited the URL of a specification.');
INSERT INTO KarmaAction (category, name, points, title, summary) VALUES (6, 'specseries', 5, 'Targeted Specification to Series', 'The user has targetted a specification to a particular series.');
INSERT INTO KarmaAction (category, name, points, title, summary) VALUES (6, 'specrelease', 5, 'Targeted Specification to Release', 'The user has targetted a specification to a particular distribution release.');
INSERT INTO KarmaAction (category, name, points, title, summary) VALUES (6, 'specmilestone', 5, 'Targeted Specification to Milestone', 'The user has targetted a specification to a particular milestone.');
INSERT INTO KarmaAction (category, name, points, title, summary) VALUES (6, 'specdraft', 3, 'Specification Drafting', 'The user has changed the status of the specification to indicate that drafting has begun.');
INSERT INTO KarmaAction (category, name, points, title, summary) VALUES (6, 'specpendingapproval', 15, 'Specification is Pending Approval', 'The user has set the status of the spec to PendingApproval');
INSERT INTO KarmaAction (category, name, points, title, summary) VALUES (6, 'specreviewed', 10, 'Specification Review', 'The user has completed a review of a specification.');
INSERT INTO KarmaAction (category, name, points, title, summary) VALUES (6, 'specbugadded', 10, 'Linked Bug to Specification', 'The user has indicated that a particular bug is related to a specification.');
INSERT INTO KarmaAction (category, name, points, title, summary) VALUES (6, 'specbugremoved', 10, 'Removed Bug from Specification', 'The user has indicated that a particular bug is not related to a specification.');

INSERT INTO LaunchpadDatabaseRevision VALUES (25,78,0);
