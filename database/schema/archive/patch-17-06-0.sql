SET client_min_messages=ERROR;

create index changeset_name_idx on changeset(name);

-- Fix the UNIQUE(id,branch) key on changeset, as used as a foreign key by
-- other tables, so that branch is the first column and PostgreSQL can
-- use this index to lookup changesets via branch
/*
This patch is being rolled out to production immediatly. We can't do
the alter tables though until we bounce the db, so I'll create some
temporary indexes to improve importd performace in this patch and
sort the unique constraints in a subsequent patch.

alter table changeset add constraint changeset_branch_key unique (branch,id);
alter table archconfigentry drop constraint archconfigentry_changeset_fk;
alter table archconfigentry add constraint archconfigentry_changeset_fk
    foreign key (branch, changeset) references changeset(branch, id);

alter table archarchive add constraint archarchive_name_key unique (name);
*/
create index temp_changeset_branch_idx on changeset(branch);
create unique index temp_archarchive_name_key on archarchive(name);

create index archnamespace_archarchive_idx on archnamespace(archarchive);
create index archnamespace_category_idx on archnamespace(category);
create index archnamespace_branch_idx on archnamespace(branch);
create index archnamespace_version_idx on archnamespace(version);

create index branch_archnamespace_idx on branch(archnamespace);


-- Rosetta index
create index potranslationsighting_datelastactive_idx
    on potranslationsighting(datelastactive);

insert into launchpaddatabaserevision values (17, 6, 0);

