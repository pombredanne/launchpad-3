SET client_min_messages=ERROR;

alter table distrorelease drop constraint distrorelease_name_key;
alter table distrorelease add constraint distrorelease_distribution_key
    unique(distribution, name);

alter table distrorelease drop constraint "$1";
alter table distrorelease drop constraint "$2";
alter table distrorelease drop constraint "$3";
alter table distrorelease drop constraint "$4";
alter table distrorelease drop constraint "$5";
alter table distrorelease add constraint distrorelease_owner_fk
    foreign key (owner) references person;
alter table distrorelease add constraint distrorelease_parentrelease_fk
    foreign key (parentrelease) references distrorelease;
alter table distrorelease add constraint distrorelease_sections_fk
    foreign key (sections) references schema;
alter table distrorelease add constraint distrorelease_components_fk
    foreign key (components) references schema;
alter table distrorelease add constraint distrorelease_distribution_fk
    foreign key (distribution) references distribution;

insert into launchpaddatabaserevision values (14,4,0);

