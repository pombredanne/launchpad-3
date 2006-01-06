SET client_min_messages=ERROR;

/* Create a load of indexes on foreign key references to the Person table.
The goal is to stop timeouts occuring in the people merge code, which
needs to do full table scans on any person reference that is not indexed
*/

create index pofile_rawimporter_idx on pofile(rawimporter);
create index pofile_owner_idx on pofile(owner);
create index pofile_lasttranslator_idx on pofile(lasttranslator);
create index branch_owner_idx on branch(owner);
create index branch_author_idx on branch(author);
create index bug_owner_idx on bug(owner);
create index distrocomponentuploader_uploader_idx on distrocomponentuploader(uploader);
create index ircid_person_idx on ircid(person);
create index jabberid_person_idx on jabberid(person);
create index maintainership_maintainer_idx on maintainership(maintainer);
create index person_merged_idx on person(merged);
create index pocomment_person_idx on pocomment(person);
create index potemplate_rawimporter_idx on potemplate(rawimporter);
create index potemplate_owner_idx on potemplate(owner);
create index product_owner_idx on product(owner);
create index productrelease_owner_idx on productrelease(owner);
create index project_owner_idx on project(owner);
create index revision_owner_idx on revision(owner);
create index shippingrequest_whoapproved_idx on shippingrequest(whoapproved);
create index shippingrequest_whocancelled_idx on shippingrequest(whocancelled);
create index signedcodeofconduct_owner_idx on signedcodeofconduct(owner);
create index sourcepackagerelease_maintainer_idx on sourcepackagerelease(maintainer);
create index sourcepackagerelease_creator_idx on sourcepackagerelease(creator);
create index specification_assignee_idx on specification(assignee);
create index specification_drafter_idx on specification(drafter);
create index specification_approver_idx on specification(approver);
create index specificationfeedback_requester_idx on specificationfeedback(requester);

INSERT INTO LaunchpadDatabaseRevision VALUES (40, 5, 1);

