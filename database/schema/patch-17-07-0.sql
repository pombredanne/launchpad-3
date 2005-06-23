SET client_min_messages=ERROR;

alter table changeset add constraint changeset_branch_key unique (branch,id);
alter table archconfigentry drop constraint archconfigentry_changeset_fk;
alter table archconfigentry add constraint archconfigentry_changeset_fk
    foreign key (branch, changeset) references changeset(branch, id);

alter table archarchive add constraint archarchive_name_key unique (name);

drop index temp_changeset_branch_idx;
drop index temp_archarchive_name_key;

insert into launchpaddatabaserevision values (17, 7, 0);

