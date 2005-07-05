/*
  Add Comments to Launchpad database
*/

-- Project
COMMENT ON TABLE Project IS 'Project: A DOAP Project. This table is the core of the DOAP section of the Launchpad database. It contains details of a single open source Project and is the anchor point for products, potemplates, and translationefforts.';
COMMENT ON COLUMN Project.owner IS 'The owner of the project will initially be the person who creates this Project in the system. We will encourage upstream project leaders to take on this role. The Project owner is able to edit the project.';
COMMENT ON COLUMN Project.summary IS 'A brief summary of this project. This
will be displayed in bold text just above the description and below the
title. It should be a single paragraph of not more than 80 words.';
COMMENT ON COLUMN Project.description IS 'A detailed description of this
project. This should primarily be focused on the organisational aspects of
the project, such as the people involved and the structures that the project
uses to govern itself. It might refer to the primary products of the project
but the detailed descriptions of those products should be in the
Product.description field, not here. So, for example, useful information
such as the dates the project was started and the way the project
coordinates itself are suitable here.';
COMMENT ON COLUMN Project.homepageurl IS 'The home page URL of this project. Note that this could well be the home page of the main product of this project as well, if the project is too small to have a separate home page for project and product.';
COMMENT ON COLUMN Project.wikiurl IS 'This is the URL of a wiki that includes information about the project. It might be a page in a bigger wiki, or it might be the top page of a wiki devoted to this project.';
COMMENT ON COLUMN Project.lastdoap IS 'This column stores a cached copy of the last DOAP description we saw for this project. We cache the last DOAP fragment for this project because there may be some aspects of it which we are unable to represent in the database (such as multiple homepageurl\'s instead of just a single homepageurl) and storing the DOAP file allows us to re-parse it later and recover this information when our database model has been updated appropriately.';
COMMENT ON COLUMN Project.name IS 'A short lowercase name uniquely identifying the product. Use cases include being used as a key in URL traversal.';
COMMENT ON COLUMN Project.sourceforgeproject IS 'The SourceForge project name for this project. This is not unique as SourceForge doesn\'t use the same project/product structure as DOAP.';
COMMENT ON COLUMN Project.freshmeatproject IS 'The FreshMeat project name for this project. This is not unique as FreshMeat does not have the same project/product structure as DOAP';
COMMENT ON COLUMN Project.reviewed IS 'Whether or not someone at Canonical has reviewed this project.';
COMMENT ON COLUMN Project.active IS 'Whether or not this project should be considered active.';
COMMENT ON COLUMN Project.translationgroup IS 'The translation group that has permission to edit translations across all products in this project. Note that individual products may have their own translationgroup, in which case those translators will also have permission to edit translations for that product.';
COMMENT ON COLUMN Project.translationpermission IS 'The level of openness of
this project\'s translation process. The enum lists different approaches to
translation, from the very open (anybody can edit any translation in any
language) to the completely closed (only designated translators can make any
changes at all).';


-- ProjectRelationship
COMMENT ON TABLE ProjectRelationship IS 'Project Relationships. This table stores information about the way projects are related to one another in the open source world. The actual nature of the relationship is stored in the \'label\' field, and possible values are given by the ProjectRelationship enum in dbschema.py. Examples are AGGREGATES ("the Gnome Project AGGREGATES EOG and Evolution and Gnumeric and AbiWord") and SIMILAR ("the Evolution project is SIMILAR to the Mutt project").';
COMMENT ON COLUMN ProjectRelationship.subject IS 'The subject of the relationship. Relationships are generally unidirectional - A AGGREGATES B is not the same as B AGGREGATES A. In the example "Gnome AGGREGATES Evolution", Gnome is the subject.';
COMMENT ON COLUMN ProjectRelationship.object IS 'The object of the relationship. In the example "Gnome AGGREGATES Evolution", Evolution is the object.';
COMMENT ON COLUMN ProjectRelationship.label IS 'The nature of the relationship. This integer takes one of the values enumerated in dbschema.py ProjectRelationship';

-- EmailAddress
COMMENT ON COLUMN EmailAddress.email IS 'An email address used by a Person. The email address is stored in a casesensitive way, but must be case insensitivly unique.';
COMMENT ON INDEX emailaddress_person_key IS 'Ensures that a person only has one preferred email address';

-- ProjectRole
/*
COMMENT ON TABLE ProjectRole IS 'Project Roles. This table records the explicit roles that people play in an open source project, with the exception of the \'ownership\' role, which is encoded in Project.owner. Types of roles are enumerated in dbschema.py DOAPRole.';
COMMENT ON COLUMN ProjectRole.person IS 'The person playing the role.';
COMMENT ON COLUMN ProjectRole.role IS 'The role, an integer enumeration documented in dbschema.py ProjectRole.';
COMMENT ON COLUMN ProjectRole.project IS 'The project in which the person plays a role.';
*/


-- Product
COMMENT ON TABLE Product IS 'Product: a DOAP Product. This table stores core information about an open source product. In Launchpad, anything that can be shipped as a tarball would be a product, and in some cases there might be products for things that never actually ship, depending on the project. For example, most projects will have a \'website\' product, because that allows you to file a Malone bug against the project website. Note that these are not actual product releases, which are stored in the ProductRelease table.';
COMMENT ON COLUMN Product.owner IS 'The Product owner would typically be the person who createed this product in Launchpad. But we will encourage the upstream maintainer of a product to become the owner in Launchpad. The Product owner can edit any aspect of the Product, as well as appointing people to specific roles with regard to the Product. Also, the owner can add a new ProductRelease and also edit Rosetta POTemplates associated with this product.';
COMMENT ON COLUMN Product.summary IS 'A brief summary of the product. This will be displayed in bold at the top of the product page, above the description.';
COMMENT ON COLUMN Product.description IS 'A detailed description of the product, highlighting primary features of the product that may be of interest to end-users. The description may also include links and other references to useful information on the web about this product. The description will be displayed on the product page, below the product summary.';
COMMENT ON COLUMN Product.project IS 'Every Product belongs to one and only one Project, which is referenced in this column.';
COMMENT ON COLUMN Product.listurl IS 'This is the URL where information about a mailing list for this Product can be found. The URL might point at a web archive or at the page where one can subscribe to the mailing list.';
COMMENT ON COLUMN Product.programminglang IS 'This field records, in plain text, the name of any significant programming languages used in this product. There are no rules, conventions or restrictions on this field at present, other than basic sanity. Examples might be "Python", "Python, C" and "Java".';
COMMENT ON COLUMN Product.downloadurl IS 'The download URL for a Product should be the best place to download that product, typically off the relevant Project web site. This should not point at the actual file, but at a web page with download information.';
COMMENT ON COLUMN Product.lastdoap IS 'This column stores a cached copy of the last DOAP description we saw for this product. See the Project.lastdoap field for more info.';
COMMENT ON COLUMN Product.sourceforgeproject IS 'The SourceForge project name for this product. This is not unique as SourceForge doesn\'t use the same project/product structure as DOAP.';
COMMENT ON COLUMN Product.freshmeatproject IS 'The FreshMeat project name for this product. This is not unique as FreshMeat does not have the same project/product structure as DOAP';
COMMENT ON COLUMN Product.reviewed IS 'Whether or not someone at Canonical has reviewed this product.';
COMMENT ON COLUMN Product.active IS 'Whether or not this product should be considered active.';
COMMENT ON COLUMN Product.translationgroup IS 'The TranslationGroup that is responsible for translations for this product. Note that the Product may be part of a Project which also has a TranslationGroup, in which case the translators from both the product and project translation group have permission to edit the translations of this product.';
COMMENT ON COLUMN Product.translationpermission IS 'The level of openness of this product\'s translation process. The enum lists different approaches to translation, from the very open (anybody can edit any translation in any language) to the completely closed (only designated translators can make any changes at all).';
COMMENT ON COLUMN Product.releaseroot IS 'The URL to the directory which holds upstream releases for this product. This allows us to monitor the upstream site and detect new upstream release tarballs.  This URL is used when the associated ProductSeries does not have a URL to use. It is also used to find files outside of any registered series.';



-- ProductLabel
COMMENT ON TABLE ProductLabel IS 'The Product label table. We have not yet clearly defined the nature of product labels, so please do not refer to this table yet. If you have a need for tags or labels on Products, please contact Mark.';



-- ProductRole
/*
COMMENT ON TABLE ProductRole IS 'Product Roles: this table documents the roles that people play with regard to a specific product. Note that if the project only has one product then it\'s best to document these roles at the project level, not at the product level. If a project has many products, then this table allows you to identify people playing a role that is specific to one of them.';
COMMENT ON COLUMN ProductRole.person IS 'The person playing the role.';
COMMENT ON COLUMN ProductRole.role IS 'The role being played. Valid roles are documented in dbschema.py DOAPRole. The roles are exactly the same as those used for ProjectRole.';
COMMENT ON COLUMN ProductRole.product IS 'The product where the person plays this role.';
*/


-- ProductSeries
COMMENT ON TABLE ProductSeries IS 'A ProductSeries is a set of product releases that are related to a specific version of the product. Typically, each major release of the product starts a new ProductSeries. These often map to a branch in the revision control system of the project, such as "2_0_STABLE". A few conventional Series names are "head" for releases of the HEAD branch, "1.0" for releases with version numbers like "1.0.0" and "1.0.1".';
COMMENT ON COLUMN ProductSeries.name IS 'The name of the ProductSeries is like a unix name, it should not contain any spaces and should start with a letter or number. Good examples are "2.0", "3.0", "head" and "development".';
COMMENT ON COLUMN ProductSeries.summary IS 'A summary of this Product Series. A good example would include the date the series was initiated and whether this is the current recommended series for people to use. The summary is usually displayed at the top of the page, in bold, just beneath the title and above the description, if there is a description field.';
COMMENT ON COLUMN ProductSeries.importstatus IS 'A status flag which
gives the state of our efforts to import the upstream code from its revision
control system and publish that in the baz revision control system. The
allowed values are documented in dbschema.BazImportStatus.';
COMMENT ON COLUMN ProductSeries.rcstype IS 'The revision control system used
by upstream for this product series. The value is defined in
dbschema.RevisionControlSystems.  If NULL, then there should be no CVS or
SVN information attached to this productseries, otherwise the relevant
fields for CVS or SVN etc should be filled out.';
COMMENT ON COLUMN ProductSeries.cvsroot IS 'The CVS root where this
productseries hosts its code. Only used if rcstype is CVS.';
COMMENT ON COLUMN ProductSeries.cvsmodule IS 'The CVS module which contains
the upstream code for this productseries. Only used if rcstype is CVS.';
COMMENT ON COLUMN ProductSeries.cvsmodule IS 'The CVS branch that contains
the upstream code for this productseries.  Only used if rcstype is CVS.';
COMMENT ON COLUMN ProductSeries.cvstarfileurl IS 'The URL of a tarfile of
the CVS repository for this productseries. This is an optimisation of the
CVS import process - instead of hitting the server to pass us every set of
changes in history, we can sometimes arrange to be given a tarfile of the
CVS repository and then process it all locally. Once imported, we switch
back to using the CVS server for ongoing syncronization.  Only used if
rcstype is CVS.';
COMMENT ON COLUMN ProductSeries.svnrepository IS 'The URL of the SVN branch
where the upstream productseries code can be found. This single URL is the
equivalent of the cvsroot, cvsmodule and cvsbranch for CVS. Only used if
rcstype is SVN.';
COMMENT ON COLUMN ProductSeries.bkrepository IS 'The URL of the BK branch
where the upstream productseries code can be found. This single URL is the
equivalent of the cvsroot, cvsmodule and cvsbranch. Only used if rcstype is
BK.';
COMMENT ON COLUMN ProductSeries.releaseroot IS 'The URL to the directory
which holds upstream releases for this productseries. This allows us to
monitor the upstream site and detect new upstream release tarballs.';
COMMENT ON COLUMN ProductSeries.releasefileglob IS 'A fileglob that lets us
see which files in the releaseroot directory are potentially new upstream
tarball releases. For example: linux-*.*.*.gz.';
COMMENT ON COLUMN ProductSeries.releaseverstyle IS 'An enum giving the style
of this product series release version numbering system.  The options are
documented in dbschema.UpstreamReleaseVersionStyle.  Most applications use
Gnu style numbering, but there are other alternatives.';
COMMENT ON COLUMN ProductSeries.targetarchcategory IS 'The category name of
the bazaar branch to which we publish new changesets detected in the
upstream revision control system.';
COMMENT ON COLUMN ProductSeries.targetarchbranch IS 'The branch name of the
bazaar branch to which we publish new changesets detected in the upstream
revision control system.';
COMMENT ON COLUMN ProductSeries.targetarchversion IS 'The version of the
bazaar branch to which we publish new changesets detected in the upstream
revision control system.';
COMMENT ON COLUMN ProductSeries.dateprocessapproved IS 'The timestamp when
this upstream import was certified for processing. Processing means it has
passed autotesting, and is being moved towards production syncing. If the
sync goes well, it will be approved for sync and then be fully in
production.';
COMMENT ON COLUMN ProductSeries.datesyncapproved IS 'The timestamp when this
upstream import was certified for ongoing syncronisation.';
COMMENT ON COLUMN ProductSeries.dateautotested IS 'This upstream revision
control system target has passed automatic testing. It can probably be moved
towards production sync status. This date is the timestamp when it passed
the autotester. The autotester allows us to find the low hanging fruit that
is easily brought into the bazaar import system by highlighting repositories
which had no apparent difficulty in being imported.';
COMMENT ON COLUMN ProductSeries.datestarted IS 'The timestamp when we last
initiated an import test or sync of this upstream repository.';
COMMENT ON COLUMN ProductSeries.datefinished IS 'The timestamp when we last
completed an import test or sync of this upstream repository. If this is
NULL and datestarted is NOT NULL, then there is a sync in progress.';




-- ProductRelease
COMMENT ON TABLE ProductRelease IS 'A Product Release. This is table stores information about a specific \'upstream\' software release, like Apache 2.0.49 or Evolution 1.5.4.';
COMMENT ON COLUMN ProductRelease.version IS 'This is a text field containing the version string for this release, such as \'1.2.4\' or \'2.0.38\' or \'7.4.3\'.';
COMMENT ON COLUMN ProductRelease.title IS 'This is the GSV Name of this release, like \'The Warty Warthog Release\' or \'All your base-0 are belong to us\'. Many upstream projects are assigning fun names to their releases - these go in this field.';
COMMENT ON COLUMN ProductRelease.summary IS 'A summary of this ProductRelease. This should be a very brief overview of changes and highlights, just a short paragraph of text. The summary is usually displayed in bold at the top of a page for this product release, above the more detailed description or changelog.';
COMMENT ON COLUMN ProductRelease.productseries IS 'A pointer to the Product Series this release forms part of. Using a Product Series allows us to distinguish between releases on stable and development branches of a product even if they are interspersed in time.';


/*
  Rosetta
*/
-- POTMsgSet
COMMENT ON TABLE POTMsgSet IS 'POTMsgSet: This table is stores a collection of msgids without their translations and all kind of information associated to that set of messages that could be found in a potemplate file.';

COMMENT ON COLUMN POTMsgSet.primemsgid IS 'The id of a pomgsid that identify this message set.';
COMMENT ON COLUMN POTMsgSet."sequence" IS 'The position of this message set inside the potemplate.';
COMMENT ON COLUMN POTMsgSet.potemplate IS 'The potemplate where this message set is stored.';
COMMENT ON COLUMN POTMsgSet.commenttext IS 'The comment text that is associated to this message set.';
COMMENT ON COLUMN POTMsgSet.filereferences IS 'The list of files and their line number where this message set was extracted from.';
COMMENT ON COLUMN POTMsgSet.sourcecomment IS 'The comment that was extracted from the source code.';
COMMENT ON COLUMN POTMsgSet.flagscomment IS 'The flags associated with this set (like c-format).';

-- POTemplate
COMMENT ON TABLE POTemplate IS 'This table stores a pot file for a given product.';
COMMENT ON COLUMN POTemplate.rawfile IS 'The pot file itself encoded as a base64 string.';
COMMENT ON COLUMN POTemplate.rawimporter IS 'The person that attached the rawfile.';
COMMENT ON COLUMN POTemplate.daterawimport IS 'The date when the rawfile was attached.';
COMMENT ON COLUMN POTemplate.rawimportstatus IS 'The status of the import: 0 pending import, 1 imported, 2 failed.';
COMMENT ON COLUMN POTemplate.sourcepackagename IS 'A reference to a sourcepackage name from where this POTemplate comes.';
COMMENT ON COLUMN POTemplate.distrorelease IS 'A reference to the distribution from where this POTemplate comes.';
COMMENT ON COLUMN POTemplate.sourcepackageversion IS 'The sourcepackage version string from where this potemplate was imported last time with our buildd <-> Rosetta gateway.';
COMMENT ON COLUMN POTemplate.header IS 'The header of a .pot file when we import it. Most important info from it is POT-Creation-Date and custom headers.';
COMMENT ON COLUMN POTemplate.potemplatename IS 'A reference to a POTemplateName row that tells us the name/domain for this POTemplate.';
COMMENT ON COLUMN POTemplate.productrelease IS 'A reference to a ProductRelease from where this POTemplate comes.';

-- POTemplateName
COMMENT ON TABLE POTemplateName IS 'POTemplate Name. This table stores the domains/names of a set of POTemplate rows.';
COMMENT ON COLUMN POTemplateName.name IS 'The name of the POTemplate set. It must be unique';
COMMENT ON COLUMN POTemplateName.title IS 'The title we are going to use every time that we render a view of this POTemplateName row.';
COMMENT ON COLUMN POTemplateName.description IS 'A brief text about this POTemplateName so the user could know more about it.';
COMMENT ON COLUMN POTemplateName.translationdomain IS 'The translation domain name for this POTemplateName';

-- POFile
COMMENT ON TABLE POFile IS 'This table stores a PO file for a given PO template.';
COMMENT ON COLUMN POFile.rawfile IS 'The Library file alias of the PO file as imported.';
COMMENT ON COLUMN POFile.rawimporter IS 'The person that attached the raw file.';
COMMENT ON COLUMN POFile.daterawimport IS 'The date when the raw file was attached.';
COMMENT ON COLUMN POFile.rawimportstatus IS 'The status of the import. See the RosettaImportStatus schema.';
COMMENT ON COLUMN POFile.exportfile IS 'The Library file alias of an export of this PO file.';
COMMENT ON COLUMN POFile.exporttime IS 'The time at which the file referenced by exportfile was generated.';

-- POSelection
COMMENT ON TABLE POSelection IS 'This table captures the full set
of all the translations ever submitted for a given pomsgset and pluralform.
It also indicates which of those is currently active.';
COMMENT ON COLUMN POSelection.pomsgset IS 'The messageset for
which we are recording a selection.';
COMMENT ON COLUMN POSelection.pluralform IS 'The pluralform of
this selected translation.';
COMMENT ON COLUMN POSelection.activesubmission IS 'The submission which made
this the active translation in rosetta for this pomsgset and pluralform.';
COMMENT ON COLUMN POSelection.publishedsubmission IS 'The submission in which
we noted this as the current translation published in revision control (or
in the public po files for this translation template, in the package or
tarball or branch which is considered the source of it).';

-- POSubmission
COMMENT ON TABLE POSubmission IS 'This table records the fact
that we saw, or someone submitted, a particular translation for a particular
msgset under a particular licence, at a specific time.';
COMMENT ON COLUMN POSubmission.pomsgset IS 'The message set for which the
submission or sighting was made.';
COMMENT ON COLUMN POSubmission.pluralform IS 'The plural form of the
submission which was made.';
COMMENT ON COLUMN POSubmission.potranslation IS 'The translation that was
submitted or sighted.';
COMMENT ON COLUMN POSubmission.person IS 'The person that made
the submission through the web to rosetta, or the last-translator on the
pofile that we are processing, or the person who uploaded that pofile to
rosetta. In short, our best guess as to the person who is contributing that
translation.';
COMMENT ON COLUMN POSubmission.origin IS 'The source of this
translation. This indicates whether the translation was in a pofile that we
parsed (probably one published in a package or branch or tarball), or was
submitted through the web.';
COMMENT ON COLUMN POSubmission.validationstatus IS 'Says whether or not we have validated this translation. Its value is specified by dbschema.TranslationValidationStatus, with 0 the value that says this row has not been validated yet.';

-- POMsgSet
COMMENT ON COLUMN POMsgSet.publishedfuzzy IS 'This indicates that this
POMsgSet was fuzzy when it was last imported from a published PO file. By
comparing the current fuzzy state (in the "fuzzy" field) to that, we know if
we have changed the fuzzy condition of the messageset in Rosetta.';
COMMENT ON COLUMN POMsgSet.publishedcomplete IS 'This indicates that this
POMsgSet was complete when it was last imported from a published PO file. By
"complete" we mean "has a translation for every expected plural form". We
can compare the current completeness state (in the "iscomplete" field) to
this, to know if we have changed the completeness of the messageset in
Rosetta since it was imported.';
COMMENT ON COLUMN POMsgSet.isfuzzy IS 'This indicates if the msgset is
currently fuzzy in Rosetta. The other indicator, publishedfuzzy, shows the
same status for the last published pofile we pulled in.';
COMMENT ON COLUMN POMsgSet.iscomplete IS 'This indicates if we believe that
Rosetta has an active translation for every expected plural form of this
message set.';


/*
  Bazaar
*/
COMMENT ON TABLE Manifest IS 'A Manifest describes the branches that go into
making up a source package or product release. This allows us to describe
the source package or product release in a way that HCT can pull down the
sources directly from The Bazaar and allow people to branch and edit
immediately. Note that a Manifest does not have an owner, please ensure that
ANYTHING that points TO a manifest, such as ProductRelease or
SourcePackageRelease, has an owner, so that we do not end up with orphaned
manifests.';



/*
  Malone
*/
COMMENT ON TABLE Bug IS 'A software bug that requires fixing. This particular bug may be linked to one or more products or source packages to identify the location(s) that this bug is found.';
COMMENT ON COLUMN Bug.name IS 'A lowercase name uniquely identifying the bug';
COMMENT ON COLUMN Bug.private IS 'Is this bug private? If so, only explicit subscribers will be able to see it';
COMMENT ON COLUMN Bug.summary IS 'A brief summary of the bug. This will be displayed at the very top of the page in bold. It will also receive a higher ranking in FTI queries than the description and comments of the bug. The bug summary is not created necessarily when the bug is filed, instead we just use the first comment as a description and allow people to fill in the summary later as they converge on a clear description of the bug itself.';
COMMENT ON COLUMN Bug.description IS 'A detailed description of the bug. Initially this will be set to the contents of the initial email or bug filing comment, but later it can be edited to give a more accurate description of the bug itself rather than the symptoms observed by the reporter.';

/* BugTask */

COMMENT ON TABLE BugTask IS 'Links a given Bug to a particular (sourcepackagename, distro) or product.';
COMMENT ON COLUMN BugTask.bug IS 'The bug that is assigned to this (sourcepackagename, distro) or product.';
COMMENT ON COLUMN BugTask.product IS 'The product in which this bug shows up.';
COMMENT ON COLUMN BugTask.sourcepackagename IS 'The name of the sourcepackage in which this bug shows up.';
COMMENT ON COLUMN BugTask.distribution IS 'The distro of the named sourcepackage.';
COMMENT ON COLUMN BugTask.status IS 'The general health of the bug, e.g. Accepted, Rejected, etc.';
COMMENT ON COLUMN BugTask.priority IS 'The importance of fixing this bug.';
COMMENT ON COLUMN BugTask.severity IS 'The impact of this bug.';
COMMENT ON COLUMN BugTask.binarypackagename IS 'The name of the binary package built from the source package. This column may only contain a value if this bug task is linked to a sourcepackage (not a product)';
COMMENT ON COLUMN BugTask.assignee IS 'The person who has been assigned to fix this bug in this product or (sourcepackagename, distro)';
COMMENT ON COLUMN BugTask.dateassigned IS 'The date on which the bug in this (sourcepackagename, distro) or product was assigned to someone to fix';
COMMENT ON COLUMN BugTask.datecreated IS 'A timestamp for the creation of this bug assignment. Note that this is not the date the bug was created (though it might be), it''s the date the bug was assigned to this product, which could have come later.';
COMMENT ON COLUMN BugTask.milestone IS 'A way to mark a bug for grouping purposes, e.g. to say it needs to be fixed by version 1.2';
COMMENT ON COLUMN BugTask.statusexplanation IS 'A place to store bug task specific information as free text';
COMMENT ON COLUMN BugTask.bugwatch IS 'This column allows us to link a bug
task to a bug watch. In other words, we are connecting the state of the task
to the state of the bug in a different bug tracking system. To the best of
our ability we\'ll try and keep the bug task syncronised with the state of
the remote bug watch.';


-- CVERef
COMMENT ON TABLE CVERef IS 'This table stores CVE references for bugs. CVE is a way of tracking security problems across multiple vendor products.';
COMMENT ON COLUMN CVERef.cveref IS 'This is the actual CVE number assigned to this specific problem.';
COMMENT ON COLUMN CVERef.owner IS 'This refers to the person who created the entry.';

-- BugExternalRef

COMMENT ON TABLE BugExternalRef IS 'A table to store web links to related content for bugs.';
COMMENT ON COLUMN BugExternalRef.bug IS 'The bug to which this URL is relevant.';
COMMENT ON COLUMN BugExternalRef.owner IS 'This refers to the person who created the link.';

/* BugInfestation */

COMMENT ON TABLE BugProductInfestation IS 'A BugProductInfestation records the impact that a bug is known to have on a specific productrelease. This allows us to track the versions of a product that are known to be affected or unaffected by a bug.';

COMMENT ON COLUMN BugProductInfestation.bug IS 'The Bug that infests this product release.';

COMMENT ON COLUMN BugProductInfestation.productrelease IS 'The product (software) release that is infested with the bug. This points at the specific release version, such as "apache 2.0.48".';

COMMENT ON COLUMN BugProductInfestation.explicit IS 'This field records whether or not the infestation was documented by a user of the system, or inferred from some other source such as the fact that it is documented to affect prior and subsequent releases of the product.';

COMMENT ON COLUMN BugProductInfestation.infestationstatus IS 'The nature of the bug infestation for this product release. Values are documented in dbschema.BugInfestationStatus, and include AFFECTED, UNAFFECTED, FIXED and VICTIMISED. See the dbschema.py file for details.';

COMMENT ON COLUMN BugProductInfestation.creator IS 'The person who recorded this infestation. Typically, this is the user who reports the specific problem on that specific product release.';

COMMENT ON COLUMN BugProductInfestation.verifiedby IS 'The person who verified that this infestation affects this specific product release.';

COMMENT ON COLUMN BugProductInfestation.dateverified IS 'The timestamp when the problem was verified on that specific release. This a small step towards a complete workflow for defect verification and management on specific releases.';

COMMENT ON COLUMN BugProductInfestation.lastmodified IS 'The timestamp when this infestation report was last modified in any way. For example, when the infestation was adjusted, or it was verified, or otherwise modified.';

COMMENT ON COLUMN BugProductInfestation.lastmodifiedby IS 'The person who touched this infestation report last, in any way.';


COMMENT ON TABLE BugPackageInfestation IS 'A BugPackageInfestation records the impact that a bug is known to have on a specific sourcepackagerelease. This allows us to track the versions of a package that are known to be affected or unaffected by a bug.';

COMMENT ON COLUMN BugPackageInfestation.bug IS 'The Bug that infests this source package release.';

COMMENT ON COLUMN BugPackageInfestation.sourcepackagerelease IS 'The package (software) release that is infested with the bug. This points at the specific source package release version, such as "apache 2.0.48-1".';

COMMENT ON COLUMN BugPackageInfestation.explicit IS 'This field records whether or not the infestation was documented by a user of the system, or inferred from some other source such as the fact that it is documented to affect prior and subsequent releases of the package.';

COMMENT ON COLUMN BugPackageInfestation.infestationstatus IS 'The nature of the bug infestation for this source package release. Values are documented in dbschema.BugInfestationStatus, and include AFFECTED, UNAFFECTED, FIXED and VICTIMISED. See the dbschema.py file for details.';

COMMENT ON COLUMN BugPackageInfestation.creator IS 'The person who recorded this infestation. Typically, this is the user who reports the specific problem on that specific package release.';

COMMENT ON COLUMN BugPackageInfestation.verifiedby IS 'The person who verified that this infestation affects this specific package.';

COMMENT ON COLUMN BugPackageInfestation.dateverified IS 'The timestamp when the problem was verified on that specific release. This a small step towards a complete workflow for defect verification and management on specific releases.';

COMMENT ON COLUMN BugPackageInfestation.lastmodified IS 'The timestamp when this infestation report was last modified in any way. For example, when the infestation was adjusted, or it was verified, or otherwise modified.';

COMMENT ON COLUMN BugPackageInfestation.lastmodifiedby IS 'The person who touched this infestation report last, in any way.';

COMMENT ON TABLE BugTracker IS 'A bug tracker in some other project. Malone allows us to link Malone bugs with bugs recorded in other bug tracking systems, and to keep the status of the relevant bug task in sync with the status in that upstream bug tracker. So, for example, you might note that Malone bug #43224 is the same as a bug in the Apache bugzilla, number 534536. Then when the upstream guys mark that bug fixed in their bugzilla, Malone know that the bug is fixed upstream.';
COMMENT ON COLUMN BugTracker.bugtrackertype IS 'The type of bug tracker, a pointer to the table of bug tracker types. Currently we know about debbugs and bugzilla bugtrackers, and plan to support roundup and sourceforge as well.';
COMMENT ON COLUMN BugTracker.name IS 'The unique name of this bugtracker, allowing us to refer to it directly.';
COMMENT ON COLUMN BugTracker.summary IS 'A brief summary of this bug tracker, which might for example list any interesting policies regarding the use of the bug tracker. The summary is displayed in bold at the top of the bug tracker page.';
COMMENT ON COLUMN BugTracker.title IS 'A title for the bug tracker, used in listings of all the bug trackers and also displayed at the top of the descriptive page for the bug tracker.';
COMMENT ON COLUMN BugTracker.contactdetails IS 'The contact details of the people responsible for that bug tracker. This allows us to coordinate the syncing of bugs to and from that bug tracker with the responsible people on the other side.';
COMMENT ON COLUMN BugTracker.baseurl IS 'The base URL for this bug tracker. Using our knowledge of the bugtrackertype, and the details in the BugWatch table we are then able to calculate relative URL\'s for relevant pages in the bug tracker based on this baseurl.';
COMMENT ON COLUMN BugTracker.owner IS 'The person who created this bugtracker entry and who thus has permission to modify it. Ideally we would like this to be the person who coordinates the running of the actual bug tracker upstream.';

/* Soyuz */

COMMENT ON COLUMN SourcePackageName.name IS
    'A lowercase name identifying one or more sourcepackages';
COMMENT ON COLUMN BinaryPackageName.name IS
    'A lowercase name identifying one or more binarypackages';
COMMENT ON COLUMN BinaryPackage.architecturespecific IS 'This field indicates whether or not a binarypackage is architecture-specific. If it is not specific to any given architecture then it can automatically be included in all the distroarchreleases which pertain.';


/* Distribution */

COMMENT ON COLUMN Distribution.lucilleconfig IS 'Configuration
information which lucille will use when processing uploads and
generating archives for this distribution';
COMMENT ON COLUMN Distribution.members IS 'Person or team with upload and commit priviledges relating to this distribution. Other rights may be assigned to this role in the future.';
COMMENT ON COLUMN Distribution.translationgroup IS 'The translation group that is responsible for all translation work in this distribution.';
COMMENT ON COLUMN Distribution.translationpermission IS 'The level of openness of this distribution\'s translation process. The enum lists different approaches to translation, from the very open (anybody can edit any translation in any language) to the completely closed (only designated translators can make any changes at all).';

/* DistroRelease */

COMMENT ON COLUMN DistroRelease.lucilleconfig IS 'Configuration
information which lucille will use when processing uploads and
generating archives for this distro release';
COMMENT ON COLUMN DistroRelease.summary IS 'A brief summary of the distro release. This will be displayed in bold at the top of the distrorelease page, above the distrorelease description. It should include any high points that are particularly important to draw to the attention of users.';
COMMENT ON COLUMN DistroRelease.description IS 'An extensive list of the features in this release of the distribution. This will be displayed on the main distro release page, below the summary.';
COMMENT ON COLUMN DistroRelease.datelastlangpack IS
'The date we last generated a base language pack for this release. Language
update packs for this release will only include translations added after that
date.';

/* ArchArchive */

COMMENT ON COLUMN ArchArchive.name IS 'The archive name, usually in the format of an email address';



-- DistroQueue
COMMENT ON TABLE DistroReleaseQueue IS 'An upload queue item. This table stores information pertaining to in-progress package uploads to a given DistroRelease.';

COMMENT ON COLUMN DistroReleaseQueue.status IS 'This is an integer field containing the current queue status of the queue item. Possible values are given by the DistroQueueStatus class in dbschema.py';

COMMENT ON COLUMN DistroReleaseQueue.distrorelease IS 'This integer field refers to the DistroRelease to which this upload is targetted';

-- DistroQueueSource
COMMENT ON TABLE DistroReleaseQueueSource IS 'An upload queue source package. This table stores information pertaining to the source files in an in-progress package upload.';

COMMENT ON COLUMN DistroReleaseQueueSource.distroreleasequeue IS 'This integer field refers to the DistroQueue row that this source belongs to.';

COMMENT ON COLUMN DistroReleaseQueueSource.sourcepackagerelease IS 'This integer field refers to the SourcePackageRelease record related to this upload.';

-- DistroQueueBuild
COMMENT ON TABLE DistroReleaseQueueBuild IS 'An upload queue binary build. This table stores information pertaining to the builds in an in-progress package upload.';

COMMENT ON COLUMN DistroReleaseQueueBuild.distroreleasequeue IS 'This integer field refers to the DistroQueue row that this source belongs to.';

COMMENT ON COLUMN DistroReleaseQueueBuild.build IS 'This integer field refers to the Build record related to this upload.';

-- SourcePackageRelease
COMMENT ON COLUMN SourcePackageRelease.section IS 'This integer field references the Section which the source package claims to be in';

/* SourcePackagePublishing and PackagePublishing */

COMMENT ON COLUMN SourcePackagePublishing.datepublished IS 'This column contains the timestamp at which point the SourcePackageRelease progressed from a pending publication to being published in the respective DistroRelease';

COMMENT ON COLUMN SourcePackagePublishing.scheduleddeletiondate IS 'This column is only used when the the publishing record is PendingRemoval. It indicates the earliest time that this record can be removed. When a publishing record is removed, the files it embodies are made candidates for removal from the pool.';

COMMENT ON COLUMN SourcePackagePublishing.datepublished IS 'This column contains the timestamp at which point the Build progressed from a pending publication to being published in the respective DistroRelease';

COMMENT ON COLUMN SourcePackagePublishing.scheduleddeletiondate IS 'This column is only used when the the publishing record is PendingRemoval. It indicates the earliest time that this record can be removed. When a publishing record is removed, the files it embodies are made candidates for removal from the pool.';

COMMENT ON COLUMN SourcePackagePublishing.status IS 'This column contains the status of the publishing record. The valid states are described in dbschema.py in PackagePublishingStatus. Example states are "Pending" and "Published"';

COMMENT ON COLUMN PackagePublishing.status IS 'This column contains the status of the publishing record. The valid states are described in dbschema.py in PackagePublishingStatus. Example states are "Pending" and "Published"';

-- PackagePublishingHistory
COMMENT ON TABLE PackagePublishingHistory IS 'PackagePublishingHistory: The history of a PackagePublishing record. This table represents the lifetime of a publishing record from inception to deletion. Records are never removed from here and in time the publishing table may become a view onto this table. A column being NULL indicates there''s no data for that state transition. E.g. a package which is removed without being superseded won''t have datesuperseded or supersededby filled in.';
COMMENT ON COLUMN PackagePublishingHistory.binarypackage IS 'The binarypackage being published.';
COMMENT ON COLUMN PackagePublishingHistory.distroarchrelease IS 'The distroarchrelease into which the binarypackage is being published.';
COMMENT ON COLUMN PackagePublishingHistory.status IS 'The current status of the publishing.';
COMMENT ON COLUMN PackagePublishingHistory.component IS 'The component into which the publishing takes place.';
COMMENT ON COLUMN PackagePublishingHistory.section IS 'The section into which the publishing takes place.';
COMMENT ON COLUMN PackagePublishingHistory.priority IS 'The priority at which the publishing takes place.';
COMMENT ON COLUMN PackagePublishingHistory.datecreated IS 'The date/time on which the publishing record was created.';
COMMENT ON COLUMN PackagePublishingHistory.datepublished IS 'The date/time on which the source was actually published into an archive.';
COMMENT ON COLUMN PackagePublishingHistory.datesuperseded IS 'The date/time on which the source was superseded by a new source.';
COMMENT ON COLUMN PackagePublishingHistory.supersededby IS 'The build which superseded this package. This seems odd but it is important because a new build may not actually build a given binarypackage and we need to supersede it appropriately';
COMMENT ON COLUMN PackagePublishingHistory.datemadepending IS 'The date/time on which this publishing record was made to be pending removal from the archive.';
COMMENT ON COLUMN PackagePublishingHistory.scheduleddeletiondate IS 'The date/time at which the package is/was scheduled to be deleted.';
COMMENT ON COLUMN PackagePublishingHistory.dateremoved IS 'The date/time at which the package was actually deleted.';
COMMENT ON COLUMN PackagePublishingHistory.pocket IS 'The pocket into which this record is published. The PLAIN pocket (zero) provides behaviour as normal. Other pockets may append things to the distrorelease name such as the UPDATES pocket (-updates) or the SECURITY pocket (-security).';
COMMENT ON COLUMN PackagePublishingHistory.embargo IS 'The publishing record is embargoed from publication if this is set to TRUE. When TRUE, this column prevents the publication record from even showing up in the publishing tables.';
COMMENT ON COLUMN PackagePublishingHistory.embargolifted IS 'The date and time when we lifted the embargo on this publishing record. I.E. when embargo was set to FALSE having previously been set to TRUE.';
COMMENT ON VIEW PackagePublishingPublicHistory IS 'View on PackagePublishingHistory that restricts access to embargoed entries';

-- PersonLanguage
COMMENT ON TABLE PersonLanguage IS 'PersonLanguage: This table stores the preferred languages that a Person has, it''s used in Rosetta to select the languages that should be showed to be translated.';
COMMENT ON COLUMN PersonLanguage.person IS 'This field is a reference to a Person object that has this preference.';
COMMENT ON COLUMN PersonLanguage.language IS 'This field is a reference to a Language object that says that the Person associated to this row knows how to translate/understand this language.';

-- soyuz views
COMMENT ON VIEW VSourcePackageInDistro IS 'This view allows us to answer the question: what source packages have releases in a certain distribution. This is an interesting case of where a view can actually solve a problem that SQLObject can''t -- there is no way of doing this query (that I see at least) in regular sqlos because there is no DISTINCT and no way to filter things without iterating in
Python (which generates N queries and we don''t want to go down that route).';
COMMENT ON VIEW VSourcePackageReleasePublishing IS 'This view simplifies a lot of queries relating to publishing and is for use as a replacement for SourcePackageRelease (I actually intend to move it to a subclass of SourcePackageRelease, because using a View in place of a real table is bizarre).';
COMMENT ON VIEW PublishedPackageView IS
    'A very large view that brings together all the information about
    packages that are currently being published within a distribution. This
    view was designed for the page which shows packages published in the
    distribution, but may be more widely used.';

-- ProcessorFamily

COMMENT ON TABLE ProcessorFamily IS 'An architecture, that might consist of several actual processors. Different distributions call these architectures different things, so we have an "architecturetag" in DistroArchRelease that might be different to the architecture\'s name.';
COMMENT ON COLUMN ProcessorFamily.name IS 'The name of the architecture. This is a short unix-style name such as i386 or amd64';
COMMENT ON COLUMN ProcessorFamily.title IS 'A title for the architecture. For example "Intel i386 Compatible".';
COMMENT ON COLUMN ProcessorFamily.description IS 'A description for this processor family. It might include any gotchas such as the fact that i386 does not necessarily mean that code would run on a 386... Ubuntu for example requires a 486.';
COMMENT ON COLUMN ProcessorFamily.owner IS 'The person responsible for this processor family entry.';

-- Processor

COMMENT ON TABLE Processor IS 'A single processor for which code might be compiled. For example, i386, P2, P3, P4, Itanium1, Itanium2... each processor belongs to a ProcessorFamily, and it might be that a package is compiled several times for a given Family, with different optimisation settings for each processor.';
COMMENT ON COLUMN Processor.name IS 'The name of this processor, for example, i386, Pentium, P2, P3, P4, Itanium, Itanium2, K7, Athlon, Opteron... it should be short and unique.';
COMMENT ON COLUMN Processor.family IS 'The ProcessorFamily for this Processor.';

-- DistroArchRelease

COMMENT ON COLUMN DistroArchRelease.processorfamily IS 'A link to the ProcessorFamily table, giving the architecture of this DistroArchRelease.';
COMMENT ON COLUMN DistroArchRelease.architecturetag IS 'The name of this architecture in the context of this specific distro release. For example, some distributions might label amd64 as amd64, others might call is x86_64. This information is used, for example, in determining the names of the actual package files... such as the "amd64" part of "apache2_2.0.56-1_amd64.deb"';

-- LauncpadDatabaseRevision
COMMENT ON TABLE LaunchpadDatabaseRevision IS 'This table has a single row which specifies the most recently applied patch number.';
COMMENT ON COLUMN LaunchpadDatabaseRevision.major IS 'Major number. This is incremented every update to production.';
COMMENT ON COLUMN LaunchpadDatabaseRevision.minor IS 'Minor number. Patches made during development each increment the minor number.';
COMMENT ON COLUMN LaunchpadDatabaseRevision.patch IS 'The patch number will hopefully always be ''0'', as it exists to support emergency patches made to the production server. eg. If production is running ''4.0.0'' and needs to have a patch applied ASAP, we would create a ''4.0.1'' patch and roll it out. We then may need to refactor all the existing ''4.x.0'' patches.';

-- Person
COMMENT ON TABLE Person IS 'Central user and group storage. A row represents a person if teamowner is NULL, and represents a team (group) if teamowner is set.';
COMMENT ON COLUMN Person.displayname IS 'Person or group''s name as it should be rendered to screen';
COMMENT ON COLUMN Person.givenname IS 'Component of a person''s full name used for secondary sorting. Generally the person''s given or christian name.';
COMMENT ON COLUMN Person.familyname IS 'Component of a person''s full name used for sorting. Generally the person''s family name.';
COMMENT ON COLUMN Person.password IS 'SSHA digest encrypted password.';
COMMENT ON COLUMN Person.teamowner IS 'id of the team owner. Team owners will have authority to add or remove people from the team.';
COMMENT ON COLUMN Person.teamdescription IS 'Informative description of the team. Format and restrictions are as yet undefined.';
COMMENT ON COLUMN Person.name IS 'Short mneumonic name uniquely identifying this person or team. Useful for url traversal or in places where we need to unambiguously refer to a person or team (as displayname is not unique).';
COMMENT ON COLUMN Person.language IS 'Preferred language for this person (unset for teams). UI should be displayed in this language wherever possible.';

-- Karma
COMMENT ON TABLE Karma IS 'Used to quantify all the ''operations'' a user performs inside the system, which maybe reporting and fixing bugs, uploading packages, end-user support, wiki editting, etc.';
COMMENT ON COLUMN Karma.action IS 'A foreign key to the KarmaAction table.';
COMMENT ON COLUMN Karma.datecreated IS 'A timestamp for the assignment of this Karma.';
COMMENT ON COLUMN Karma.Person IS 'The Person for wich this Karma was assigned.';

-- KarmaAction
COMMENT ON TABLE KarmaAction IS 'Stores all the actions that would give karma to the user which performed it.';
COMMENT ON COLUMN KarmaAction.name IS 'The unique name of this action.';
COMMENT ON COLUMN KarmaAction.category IS 'A dbschema value used to group actions together.';
COMMENT ON COLUMN KarmaAction.points IS 'The number of points this action is worth of.';

-- KarmaCache
COMMENT ON TABLE KarmaCache IS 'Stores a cached value of a person\'s karma points, grouped by the action category.';
COMMENT ON COLUMN KarmaCache.Person IS 'The person which performed the actions of this category, and thus got the karma.';
COMMENT ON COLUMN KarmaCache.Category IS 'The category of the actions.';
COMMENT ON COLUMN KarmaCache.KarmaValue IS 'The karma points of all actions of this category performed by this person.';

-- Bounty
COMMENT ON TABLE Bounty IS 'A set of bounties for work to be done by the open source community. These bounties will initially be offered only by Canonical, but later we will create the ability for people to offer the bounties themselves, using us as a clearing house.';
COMMENT ON COLUMN Bounty.usdvalue IS 'This is the ESTIMATED value in US Dollars of the bounty. We say "estimated" because the bounty might one day be offered in one of several currencies, or people might contribute different amounts in different currencies to each bounty. This field will reflect an estimate based on recent currency exchange rates of the value of this bounty in USD.';
COMMENT ON COLUMN Bounty.difficulty IS 'An estimate of the difficulty of the bounty, from 1 to 100, where 100 is extremely difficult and 1 is extremely easy.';
COMMENT ON COLUMN Bounty.duration IS 'An estimate of the length of time it should take to complete this bounty, given the skills required.';
COMMENT ON COLUMN Bounty.reviewer IS 'The person who will review this bounty regularly for progress. The reviewer is the person who is responsible for establishing when the bounty is complete.';
COMMENT ON COLUMN Bounty.owner IS 'The person who created the bounty. The owner can update the specification of the bounty, and appoints the reviewer.';

COMMENT ON TABLE BountySubscription IS 'This table records whether or not someone it interested in a bounty. Subscribers will show up on the page with the bounty details.';
COMMENT ON COLUMN BountySubscription.bounty IS 'The bounty to which the person is subscribed.';
COMMENT ON COLUMN BountySubscription.person IS 'The person being subscribed to this bounty.';
COMMENT ON COLUMN BountySubscription.subscription IS 'The nature of the subscription. A NULL value indicates that this subscription has been nullified, and is as if there was no subscription record at all.';

COMMENT ON TABLE ProductBounty IS 'This table records a simple link between a bounty and a product. This bounty will be listed on the product web page, and the product will be mentioned on the bounty web page.';

COMMENT ON TABLE DistroBounty IS 'This table records a simple link between a bounty and a distribution. This bounty will be listed on the distribution web page, and the distribution will be mentioned on the bounty web page.';

COMMENT ON TABLE ProjectBounty IS 'This table records a simple link between a bounty and a project. This bounty will be listed on the project web page, and the project will be mentioned on the bounty web page.';

-- Maintainership

COMMENT ON TABLE Maintainership IS 'Stores the maintainer information for a
sourcepackage in a particular distribution. Note that this does not store
the information per-distrorelease, but for the overall "distribution", which
generally refers to the current development release of the distro.';

COMMENT ON COLUMN Maintainership.maintainer IS 'Refers to the person
responsible for this sourcepackage inside this distribution. Note that the
"maintainer" for a package varies over time, so the person who was
responsible in a previous distrorelease may no longer be listed as
a maintainer.';

-- Messaging subsytem
COMMENT ON TABLE BugMessage IS 'This table maps a message to a bug. In other words, it shows that a particular message is associated with a particular bug.';
COMMENT ON TABLE Message IS 'This table stores a single RFC822-style message. Messages can be threaded (using the parent field). These messages can then be referenced from elsewhere in the system, such as the BugMessage table, integrating messageboard facilities with the rest of The Launchpad.';
COMMENT ON COLUMN Message.parent IS 'A "parent message". This allows for some level of threading in Messages.';
COMMENT ON COLUMN Message.title IS 'The title text of the message, or the subject if it was an email.';
COMMENT ON COLUMN Message.distribution IS 'The distribution in which this message originated, if we know it.';
COMMENT ON COLUMN Message.raw IS 'The original unadulterated message if it arrived via email. This is required to provide access to the original, undecoded message.';

COMMENT ON TABLE MessageChunk IS 'This table stores a single chunk of a possibly multipart message. There will be at least one row in this table for each message. text/* parts are stored in the content column. All other parts are stored in the Librarian and referenced via the blob column. If both content and blob are NULL, then this chunk has been removed (eg. offensive, legal reasons, virus etc.)';
COMMENT ON COLUMN MessageChunk.content IS 'Text content for this chunk of the message. This content is full text searchable.';
COMMENT ON COLUMN MessageChunk.blob IS 'Binary content for this chunk of the message.';
COMMENT ON COLUMN MessageChunk.sequence IS 'Order of a particular chunk. Chunks are orders in ascending order starting from 1.';

-- Comments on Lucille views
COMMENT ON VIEW SourcePackageFilePublishing IS 'This view is used mostly by Lucille while performing publishing and unpublishing operations. It lists all the files associated with a sourcepackagerelease and collates all the textual representations needed for publishing components etc to allow rapid queries from SQLObject.';
COMMENT ON VIEW BinaryPackageFilePublishing IS 'This view is used mostly by Lucille while performing publishing and unpublishing operations. It lists all the files associated with a binarypackage and collates all the textual representations needed for publishing components etc to allow rapid queries from SQLObject.';
COMMENT ON VIEW SourcePackagePublishingView IS 'This view is used mostly by Lucille while performing publishing¸ unpublishing, domination, superceding and other such operations. It provides an ID equal to the underlying SourcePackagePublishing record to permit as direct a change to publishing details as is possible. The view also collates useful textual data to permit override generation etc.';
COMMENT ON VIEW BinaryPackagePublishingView IS 'This view is used mostly by Lucille while performing publishing¸ unpublishing, domination, superceding and other such operations. It provides an ID equal to the underlying PackagePublishing record to permit as direct a change to publishing details as is possible. The view also collates useful textual data to permit override generation etc.';

-- SourcePackageRelease

COMMENT ON TABLE SourcePackageRelease IS 'SourcePackageRelease: A source
package release. This table represents a specific release of a source
package. Source package releases may be published into a distrorelease, or
even multiple distroreleases.';
COMMENT ON COLUMN SourcePackageRelease.creator IS 'The creator of this
sourcepackagerelease. This is the person referred to in the top entry in the
package changelog in debian terms. Note that a source package maintainer in
Ubuntu might be person A, but a particular release of that source package
might in fact have been created by a different person B. The maintainer
would be recorded in the Maintainership table, while the creator of THIS
release would be recorded in the SourcePackageRelease.creator field.';
COMMENT ON COLUMN SourcePackageRelease.version IS 'The version string for
this source package release. E.g. "1.0-2" or "1.4-5ubuntu9.1". Note that, in
ubuntu-style and redhat-style distributions, the version+sourcepackagename
is unique, even across distroreleases. In other words, you cannot have a
foo-1.2-1 package in Hoary that is different from foo-1.2-1 in Warty.';
COMMENT ON COLUMN SourcePackageRelease.dateuploaded IS 'The date/time that
this sourcepackagerelease was first uploaded to the Launchpad.';
COMMENT ON COLUMN SourcePackageRelease.urgency IS 'The urgency of the
upload. This is generally used to prioritise buildd activity but may also be
used for "testing" systems or security work in the future. The "urgency" is
set by the uploader, in the DSC file.';
COMMENT ON COLUMN SourcePackageRelease.dscsigningkey IS 'The GPG key used to
sign the DSC. This is not necessarily the maintainer\'s key, or the
creator\'s key. For example, it\'s possible to produce a package, then ask a
sponsor to upload it.';
COMMENT ON COLUMN SourcePackageRelease.component IS 'The component in which
this sourcepackagerelease is intended (by the uploader) to reside. E.g.
main, universe, restricted. Note that the distribution managers will often
override this data and publish the package in an entirely different
component.';
COMMENT ON COLUMN SourcePackageRelease.changelog IS 'The changelog of this
source package release.';
COMMENT ON COLUMN SourcePackageRelease.builddepends IS 'The build
dependencies for this source package release.';
COMMENT ON COLUMN SourcePackageRelease.builddependsindep IS 'The
architecture-independant build dependancies for this source package release.';
COMMENT ON COLUMN SourcePackageRelease.architecturehintlist IS 'The
architectures which this source package release believes it should be built.
This is used as a hint to the build management system when deciding what
builds are still needed.';
COMMENT ON COLUMN SourcePackageRelease.format IS 'The format of this
sourcepackage release, e.g. DPKG, RPM, EBUILD, etc. This is an enum, and the
values are listed in dbschema.SourcePackageFormat';
COMMENT ON COLUMN SourcePackageRelease.dsc IS 'The "Debian Source Control"
file for the sourcepackagerelease, from its upload into Ubuntu for the
first time.';
COMMENT ON COLUMN SourcePackageRelease.uploaddistrorelease IS 'The
distrorelease into which this source package release was uploaded into
Launchpad / Ubuntu for the first time. In general, this will be the
development Ubuntu release into which this package was uploaded. For a
package which was unchanged between warty and hoary, this would show Warty.
For a package which was uploaded into Hoary, this would show Hoary.';



-- SourcePackageName

COMMENT ON TABLE SourcePackageName IS 'SourcePackageName: A soyuz source package name.';

-- BinaryPackage

COMMENT ON TABLE BinaryPackage IS 'BinaryPackage: A soyuz binary package representation. This table stores the records for each binary package uploaded into the system. Each sourcepackagerelease may build various binarypackages on various architectures.';
COMMENT ON COLUMN BinaryPackage.binarypackagename IS 'A reference to the name of the binary package';
COMMENT ON COLUMN BinaryPackage.version IS 'The version of the binary package. E.g. "1.0-2"';
COMMENT ON COLUMN BinaryPackage.summary IS 'A summary of the binary package. Commonly used on listings of binary packages';
COMMENT ON COLUMN BinaryPackage.description IS 'A longer more detailed description of the binary package';
COMMENT ON COLUMN BinaryPackage.build IS 'The build in which this binarypackage was produced';
COMMENT ON COLUMN BinaryPackage.binpackageformat IS 'The binarypackage format. E.g. RPM, DEB etc';
COMMENT ON COLUMN BinaryPackage.component IS 'The archive component that this binarypackage is in. E.g. main, universe etc';
COMMENT ON COLUMN BinaryPackage.section IS 'The archive section that this binarypackage is in. E.g. devel, libdevel, editors';
COMMENT ON COLUMN BinaryPackage.priority IS 'The priority that this package has. E.g. Base, Standard, Extra, Optional';
COMMENT ON COLUMN BinaryPackage.shlibdeps IS 'The shared library dependencies of this binary package';
COMMENT ON COLUMN BinaryPackage.depends IS 'The list of packages this binarypackage depends on';
COMMENT ON COLUMN BinaryPackage.recommends IS 'The list of packages this binarypackage recommends. Recommended packages often enhance the behaviour of a package.';
COMMENT ON COLUMN BinaryPackage.suggests IS 'The list of packages this binarypackage suggests.';
COMMENT ON COLUMN BinaryPackage.conflicts IS 'The list of packages this binarypackage conflicts with.';
COMMENT ON COLUMN BinaryPackage.replaces IS 'The list of packages this binarypackage replaces files in. Often this is used to provide an upgrade path between two binarypackages of different names';
COMMENT ON COLUMN BinaryPackage.provides IS 'The list of virtual packages (or real packages under some circumstances) which this binarypackage provides.';
COMMENT ON COLUMN BinaryPackage.essential IS 'Whether or not this binarypackage is essential to the smooth operation of a base system';
COMMENT ON COLUMN BinaryPackage.installedsize IS 'What the installed size of the binarypackage is. This is represented as a number of kilobytes of storage.';
COMMENT ON COLUMN BinaryPackage.copyright IS 'The copyright associated with this binarypackage. Often in the case of debian packages this is found in /usr/share/doc/<binarypackagename>/copyright';
COMMENT ON COLUMN BinaryPackage.licence IS 'The licence that this binarypackage is under.';


-- BinaryPackageFile

COMMENT ON TABLE BinaryPackageFile IS 'BinaryPackageFile: A soyuz <-> librarian link table. This table represents the ownership in the librarian of a file which represents a binary package';
COMMENT ON COLUMN BinaryPackageFile.binarypackage IS 'The binary package which is represented by the file';
COMMENT ON COLUMN BinaryPackageFile.libraryfile IS 'The file in the librarian which represents the package';
COMMENT ON COLUMN BinaryPackageFile.filetype IS 'The "type" of the file. E.g. DEB, RPM';

-- BinaryPackageName

COMMENT ON TABLE BinaryPackageName IS 'BinaryPackageName: A soyuz binary package name.';

-- OSFile

COMMENT ON TABLE OSFile IS 'OSFile: Soyuz\'s representation of files on disk. BinaryPackages put files in installations.';
COMMENT ON COLUMN OSFile.path IS 'The filepath';


-- OSFileInPackage

COMMENT ON TABLE OSFileInPackage IS 'OSFileInPackage: Soyuz\'s representation of files in packages. This table stores the metadata associated with files which can be found in binarypackages.';
COMMENT ON COLUMN OSFileInPackage.osfile IS 'The OSFile (path) in question';
COMMENT ON COLUMN OSFileInPackage.binarypackage IS 'The binarypackage which contains this';
COMMENT ON COLUMN OSFileInPackage.unixperms IS 'The unix permissions assigned to the file';
COMMENT ON COLUMN OSFileInPackage.conffile IS 'Whether or not the file is a conffile in this package';
COMMENT ON COLUMN OSFileInPackage.createdoninstall IS 'Whether or not the file is created during the installation of the package on the system. It may also be used to store jeff''s mum''s pants';

-- Distribution

COMMENT ON TABLE Distribution IS 'Distribution: A soyuz distribution. A distribution is a collection of DistroReleases. Distributions often group together policy and may be referred to by a name such as "Ubuntu" or "Debian"';
COMMENT ON COLUMN Distribution.name IS 'The unique name of the distribution as a short lowercase name suitable for use in a URL.';
COMMENT ON COLUMN Distribution.title IS 'The title of the distribution. More a "display name" as it were. E.g. "Ubuntu" or "Debian GNU/Linux"';
COMMENT ON COLUMN Distribution.description IS 'A description of the distribution. More detailed than the title, this column may also contain information about the project this distribution is run by.';
COMMENT ON COLUMN Distribution.domainname IS 'The domain name of the distribution. This may be used both for linking to the distribution and for context-related stuff.';
COMMENT ON COLUMN Distribution.owner IS 'The person in launchpad who is in ultimate-charge of this distribution within launchpad.';

-- DistroRelease

COMMENT ON TABLE DistroRelease IS 'DistroRelease: A soyuz distribution release. A DistroRelease is a given version of a distribution. E.g. "Warty" "Hoary" "Sarge" etc.';
COMMENT ON COLUMN DistroRelease.distribution IS 'The distribution which contains this distrorelease.';
COMMENT ON COLUMN DistroRelease.name IS 'The unique name of the distrorelease. This is a short name in lower case and would be used in sources.list configuration and in generated URLs. E.g. "warty" "sarge" "sid"';
COMMENT ON COLUMN DistroRelease.title IS 'The display-name title of the distrorelease E.g. "Warty Warthog"';
COMMENT ON COLUMN DistroRelease.description IS 'The long detailed description of the release. This may describe the focus of the release or other related information.';
COMMENT ON COLUMN DistroRelease.version IS 'The version of the release. E.g. warty would be "4.10" and hoary would be "5.4"';
COMMENT ON COLUMN DistroRelease.components IS 'The components which are considered valid within this distrorelease.';
COMMENT ON COLUMN DistroRelease.sections IS 'The sections which are considered valid within this distrorelease.';
COMMENT ON COLUMN DistroRelease.releasestatus IS 'The current release status of this distrorelease. E.g. "pre-release freeze" or "released"';
COMMENT ON COLUMN DistroRelease.datereleased IS 'The date on which this distrorelease was released. (obviously only valid for released distributions)';
COMMENT ON COLUMN DistroRelease.parentrelease IS 'The parent release on which this distribution is based. This is related to the inheritance stuff.';
COMMENT ON COLUMN DistroRelease.owner IS 'The ultimate owner of this distrorelease.';

-- DistroArchRelease

COMMENT ON TABLE DistroArchRelease IS 'DistroArchRelease: A soyuz distribution release for a given architecture. A distrorelease runs on various architectures. The distroarchrelease groups that architecture-specific stuff.';
COMMENT ON COLUMN DistroArchRelease.distrorelease IS 'The distribution which this distroarchrelease is part of.';

-- DistributionRole
/*
COMMENT ON TABLE DistributionRole IS 'DistributionRole: A soyuz distribution role. This table represents a role played by a specific person in a given distribution.';
COMMENT ON COLUMN DistributionRole.person IS 'The person undertaking the represented role.';
COMMENT ON COLUMN DistributionRole.distribution IS 'The distribution in which this role is undertaken';
COMMENT ON COLUMN DistributionRole.role IS 'The role that the identified person takes in the referenced distribution';
*/

-- DistroReleaseRole
/*
COMMENT ON TABLE DistroReleaseRole IS 'DistroReleaseRole: A soyuz distribution release role. This table represents a role played by a specific person in a specific distrorelease of a distribution.';
COMMENT ON COLUMN DistroReleaseRole.person IS 'The person undertaking the represented role.';
COMMENT ON COLUMN DistroReleaseRole.distrorelease IS 'The distrorelease in which the role is undertaken.';
COMMENT ON COLUMN DistroReleaseRole.role IS 'The role that the identified person undertakes in the referenced distrorelease.';
*/

-- LibraryFileContent

COMMENT ON TABLE LibraryFileContent IS 'LibraryFileContent: A librarian file\'s contents. The librarian stores files in a safe and transactional way. This table represents the contents of those files within the database.';
COMMENT ON COLUMN LibraryFileContent.datecreated IS 'The date on which this librarian file was created';
COMMENT ON COLUMN LibraryFileContent.datemirrored IS 'When the file was mirrored from the librarian onto the backup server';
COMMENT ON COLUMN LibraryFileContent.filesize IS 'The size of the file';
COMMENT ON COLUMN LibraryFileContent.sha1 IS 'The SHA1 sum of the file\'s contents';

-- LibraryFileAlias

COMMENT ON TABLE LibraryFileAlias IS 'LibraryFileAlias: A librarian file\'s alias. The librarian stores, along with the file contents, a record stating the file name and mimetype. This table represents it.';
COMMENT ON COLUMN LibraryFileAlias.content IS 'The libraryfilecontent which is the data in this file.';
COMMENT ON COLUMN LibraryFileAlias.filename IS 'The name of the file. E.g. "foo_1.0-1_i386.deb"';
COMMENT ON COLUMN LibraryFileAlias.mimetype IS 'The mime type of the file. E.g. "application/x-debian-package"';

-- PackagePublishing

COMMENT ON VIEW PackagePublishing IS 'PackagePublishing: Publishing records for Soyuz/Lucille. Lucille publishes binarypackages in distroarchreleases. This view represents the publishing of each binarypackage not yet deleted from the distroarchrelease.';
COMMENT ON COLUMN PackagePublishing.binarypackage IS 'The binarypackage which is being published';
COMMENT ON COLUMN PackagePublishing.distroarchrelease IS 'The distroarchrelease in which the binarypackage is published';
COMMENT ON COLUMN PackagePublishing.component IS 'The component in which the binarypackage is published';
COMMENT ON COLUMN PackagePublishing.section IS 'The section in which the binarypackage is published';
COMMENT ON COLUMN PackagePublishing.priority IS 'The priority at which the binarypackage is published';
COMMENT ON COLUMN PackagePublishing.scheduleddeletiondate IS 'The datetime at which this publishing entry is scheduled to be removed from the distroarchrelease';
COMMENT ON COLUMN PackagePublishing.status IS 'The current status of the packagepublishing record. For example "PUBLISHED" "PENDING" or "PENDINGREMOVAL"';

-- SourcePackagePublishing

COMMENT ON VIEW SourcePackagePublishing IS 'SourcePackagePublishing: Publishing records for Soyuz/Lucille. Lucille publishes sourcepackagereleases in distroreleases. This table represents the currently active publishing of each sourcepackagerelease. For history see SourcePackagePublishingHistory.';
COMMENT ON COLUMN SourcePackagePublishing.distrorelease IS 'The distrorelease which is having the sourcepackagerelease being published into it.';
COMMENT ON COLUMN SourcePackagePublishing.sourcepackagerelease IS 'The sourcepackagerelease being published into the distrorelease.';
COMMENT ON COLUMN SourcePackagePublishing.status IS 'The current status of the sourcepackage publishing record. For example "PUBLISHED" "PENDING" or "PENDINGREMOVAL"';
COMMENT ON COLUMN SourcePackagePublishing.component IS 'The component in which the sourcepackagerelease is published';
COMMENT ON COLUMN SourcePackagePublishing.section IS 'The section in which the sourcepackagerelease is published';
COMMENT ON COLUMN SourcePackagePublishing.scheduleddeletiondate IS 'The datetime at which this publishing entry is scheduled to be removed from the distrorelease.';
COMMENT ON COLUMN SourcePackagePublishing.datepublished IS 'THIS COLUMN IS PROBABLY UNUSED';

-- SourcePackageReleaseFile

COMMENT ON TABLE SourcePackageReleaseFile IS 'SourcePackageReleaseFile: A soyuz source package release file. This table links sourcepackagerelease records to the files which comprise the input.';
COMMENT ON COLUMN SourcePackageReleaseFile.libraryfile IS 'The libraryfilealias embodying this file';
COMMENT ON COLUMN SourcePackageReleaseFile.filetype IS 'The type of the file. E.g. TAR, DIFF, DSC';
COMMENT ON COLUMN SourcePackageReleaseFile.sourcepackagerelease IS 'The sourcepackagerelease that this file belongs to';

COMMENT ON TABLE LoginToken IS 'LoginToken stores one time tokens used for validating email addresses and other tasks that require verifying an email address is valid such as password recovery and account merging. This table will be cleaned occasionally to remove expired tokens. Expiry time is not yet defined.';
COMMENT ON COLUMN LoginToken.requester IS 'The Person that made this request. This will be null for password recovery requests.';
COMMENT ON COLUMN LoginToken.requesteremail IS 'The email address that was used to login when making this request. This provides an audit trail to help the end user confirm that this is a valid request. It is not a link to the EmailAddress table as this may be changed after the request is made. This field will be null for password recovery requests.';
COMMENT ON COLUMN LoginToken.email IS 'The email address that this request was sent to.';
COMMENT ON COLUMN LoginToken.created IS 'The timestamp that this request was made.';
COMMENT ON COLUMN LoginToken.tokentype IS 'The type of request, as per dbschema.TokenType.';
COMMENT ON COLUMN LoginToken.token IS 'The token (not the URL) emailed used to uniquely identify this request. This token will be used to generate a URL that when clicked on will continue a workflow.';
COMMENT ON COLUMN LoginToken.fingerprint IS 'The GPG key fingerprint to be validated on this transaction, it means that a new register will be created relating this given key with the requester in question. The requesteremail still passing for the same usual checks.';

COMMENT ON TABLE Milestone IS 'An identifier that helps a maintainer group together things in some way, e.g. "1.2" could be a Milestone that bazaar developers could use to mark a task as needing fixing in bazaar 1.2.';
COMMENT ON COLUMN Milestone.product IS 'The product for which this is a milestone.';
COMMENT ON COLUMN Milestone.name IS 'The identifier text, e.g. "1.2."';
COMMENT ON COLUMN Milestone.title IS 'The description of, e.g. "1.2."';

    
COMMENT ON TABLE PushMirrorAccess IS 'Records which users can update which push mirrors';
COMMENT ON COLUMN PushMirrorAccess.name IS 'Name of an arch archive on the push mirror, e.g. lord@emf.net--2003-example';
COMMENT ON COLUMN PushMirrorAccess.person IS 'A person that has access to update the named archive';

-- Builder
COMMENT ON COLUMN Builder.builderok IS 'Should a builder fail for any reason, from out-of-disk-space to not responding to the buildd master, the builderok flag is set to false and the failnotes column is filled with a reason.';
COMMENT ON COLUMN Builder.failnotes IS 'This column gets filled out with a textual description of how/why a builder has failed. If the builderok column is true then the value in this column is irrelevant and should be treated as NULL or empty.';
COMMENT ON COLUMN Builder.trusted IS 'Whether or not the builder is cleared to do SECURITY pocket builds. Such a builder will have firewall access to the embargo archives etc.';
COMMENT ON COLUMN Builder.url IS 'The url to the build slave. There may be more than one build slave on a given host so this url includes the port number to use. The default port number for a build slave is 8221';


COMMENT ON TABLE BuildQueue IS 'BuildQueue: The queue of builds in progress/scheduled to run. This table is the core of the build daemon master. It lists all builds in progress or scheduled to start.';
COMMENT ON COLUMN BuildQueue.build IS 'The build for which this queue item exists. This is how the buildd master will find all the files it needs to perform the build';
COMMENT ON COLUMN BuildQueue.builder IS 'The builder assigned to this build. Some builds will have a builder assigned to queue them up; some will be building on the specified builder already; others will not have a builder yet (NULL) and will be waiting to be assigned into a builder''s queue';
COMMENT ON COLUMN BuildQueue.created IS 'The timestamp of the creation of this row. This is used by the buildd master scheduling algorithm to decide how soon to schedule a build to run on a given builder.';
COMMENT ON COLUMN BuildQueue.buildstart IS 'The timestamp of the start of the build run on the given builder. If this is NULL then the build is not running yet.';
COMMENT ON COLUMN BuildQueue.logtail IS 'The tail end of the log of the current build. This is updated regularly as the buildd master polls the buildd slaves. Once the build is complete; the full log will be lodged with the librarian and linked into the build table.';
COMMENT ON COLUMN BuildQueue.lastscore IS 'The last score ascribed to this build record. This can be used in the UI among other places.';

-- Mirrors

COMMENT ON TABLE Mirror IS 'Stores general information about mirror sites. Both regular pull mirrors and top tier mirrors are included.';
COMMENT ON COLUMN Mirror.baseurl IS 'The base URL to the mirror, including protocol and optional trailing slash.';
COMMENT ON COLUMN Mirror.country IS 'The country where the mirror is located.';
COMMENT ON COLUMN Mirror.name IS 'Unique name for the mirror, suitable for use in URLs.';
COMMENT ON COLUMN Mirror.description IS 'Description of the mirror.';
COMMENT ON COLUMN Mirror.freshness IS 'dbschema.MirrorFreshness enumeration indicating freshness.';
COMMENT ON COLUMN Mirror.lastcheckeddate IS 'UTC timestamp of when the last check for freshness and consistency was made. NULL indicates no check has ever been made.';
COMMENT ON COLUMN Mirror.approved IS 'True if this mirror has been approved by the Ubuntu/Canonical mirror manager, otherwise False.';

COMMENT ON TABLE MirrorContent IS 'Stores which distroarchreleases and compoenents a given mirror has.';
COMMENT ON COLUMN MirrorContent.distroarchrelease IS 'A distroarchrelease that this mirror contains.';
COMMENT ON COLUMN MirrorContent.component IS 'What component of the distroarchrelease that this mirror contains.';

COMMENT ON TABLE MirrorSourceContent IS 'Stores which distrorelease and components a given mirror that includes source packages has.';
COMMENT ON COLUMN MirrorSourceContent.distrorelease IS 'A distrorelease that this mirror contains.';
COMMENT ON COLUMN MirrorSourceContent.component IS 'What component of the distrorelease that this sourcepackage mirror contains.';

-- SourcePackagePublishingHistory
COMMENT ON TABLE SourcePackagePublishingHistory IS 'SourcePackagePublishingHistory: The history of a SourcePackagePublishing record. This table represents the lifetime of a publishing record from inception to deletion. Records are never removed from here and in time the publishing table may become a view onto this table. A column being NULL indicates there''s no data for that state transition. E.g. a package which is removed without being superseded won''t have datesuperseded or supersededby filled in.';
COMMENT ON COLUMN SourcePackagePublishingHistory.sourcepackagerelease IS 'The sourcepackagerelease being published.';
COMMENT ON COLUMN SourcePackagePublishingHistory.distrorelease IS 'The distrorelease into which the sourcepackagerelease is being published.';
COMMENT ON COLUMN SourcePackagePublishingHistory.status IS 'The current status of the publishing.';
COMMENT ON COLUMN SourcePackagePublishingHistory.component IS 'The component into which the publishing takes place.';
COMMENT ON COLUMN SourcePackagePublishingHistory.section IS 'The section into which the publishing takes place.';
COMMENT ON COLUMN SourcePackagePublishingHistory.datecreated IS 'The date/time on which the publishing record was created.';
COMMENT ON COLUMN SourcePackagePublishingHistory.datepublished IS 'The date/time on which the source was actually published into an archive.';
COMMENT ON COLUMN SourcePackagePublishingHistory.datesuperseded IS 'The date/time on which the source was superseded by a new source.';
COMMENT ON COLUMN SourcePackagePublishingHistory.supersededby IS 'The source which superseded this one.';
COMMENT ON COLUMN SourcePackagePublishingHistory.datemadepending IS 'The date/time on which this publishing record was made to be pending removal from the archive.';
COMMENT ON COLUMN SourcePackagePublishingHistory.scheduleddeletiondate IS 'The date/time at which the source is/was scheduled to be deleted.';
COMMENT ON COLUMN SourcePackagePublishingHistory.dateremoved IS 'The date/time at which the source was actually deleted.';
COMMENT ON COLUMN SourcePackagePublishingHistory.pocket IS 'The pocket into which this record is published. The PLAIN pocket (zero) provides behaviour as normal. Other pockets may append things to the distrorelease name such as the UPDATES pocket (-updates) or the SECURITY pocket (-security).';
COMMENT ON COLUMN SourcePackagePublishingHistory.embargo IS 'The publishing record is embargoed from publication if this is set to TRUE. When TRUE, this column prevents the publication record from even showing up in the publishing tables.';
COMMENT ON COLUMN SourcePackagePublishingHistory.embargolifted IS 'The date and time when we lifted the embargo on this publishing record. I.E. when embargo was set to FALSE having previously been set to TRUE.';
COMMENT ON VIEW SourcePackagePublishingPublicHistory IS 'A view on SourcePackagePublishingHistory that restricts access to embargoed entries';

-- Packaging
COMMENT ON TABLE Packaging IS 'DO NOT JOIN THROUGH THIS TABLE. This is a set
of information linking upstream product series (branches) to distro
packages, but it\'s not planned or likely to be complete, in the sense that
we do not attempt to have information for every branch in every derivative
distro managed in Launchpad. So don\'t join through this table to get from
product to source package, or vice versa. Rather, use the
ProductSeries.sourcepackages attribute, or the
SourcePackage.productseries attribute. You may need to create a
SourcePackage with a given sourcepackagename and distrorelease, then use its
.productrelease attribute. The code behind those methods does more than just
join through the tables, it is also smart enough to look at related
distro\'s and parent distroreleases, and at Ubuntu in particular.';
COMMENT ON COLUMN Packaging.productseries IS 'The upstream product series
that has been packaged in this distrorelease sourcepackage.';
COMMENT ON COLUMN Packaging.sourcepackagename IS 'The source package name for
the source package that includes the upstream productseries described in
this Packaging record. There is no requirement that such a sourcepackage
actually be published in the distro.';
COMMENT ON COLUMN Packaging.distrorelease IS 'The distrorelease in which the
productseries has been packaged.';
COMMENT ON COLUMN Packaging.packaging IS 'A dbschema Enum (PackagingType)
describing the way the upstream productseries has been packaged. Generally
it will be of type PRIME, meaning that the upstream productseries is the
primary substance of the package, but it might also be INCLUDES, if the
productseries has been included as a statically linked library, for example.
This allows us to say that a given Source Package INCLUDES libneon but is a
PRIME package of tla, for example. By INCLUDES we mean that the code is
actually lumped into the package as ancilliary support material, rather
than simply depending on a separate packaging of that code.';

-- Translator / TranslationGroup

COMMENT ON TABLE TranslationGroup IS 'This represents an organised translation group that spans multiple languages. Effectively it consists of a list of people (pointers to Person), and each Person is associated with a Language. So, for each TranslationGroup we can ask the question "in this TranslationGroup, who is responsible for translating into Arabic?", for example.';
COMMENT ON TABLE Translator IS 'A translator is a person in a TranslationGroup who is responsible for a particular language. At the moment, there can only be one person in a TranslationGroup who is the Translator for a particular language. If you want multiple people, then create a launchpad team and assign that team to the language.';
COMMENT ON COLUMN Translator.translationgroup IS 'The TranslationGroup for which this Translator is working.';
COMMENT ON COLUMN Translator.language IS 'The language for which this Translator is responsible in this TranslationGroup. Note that the same person may be responsible for multiple languages, but any given language can only have one Translator within the TranslationGroup.';
COMMENT ON COLUMN Translator.translator IS 'The Person who is responsible for this language in this translation group.';

-- PocketChroot
COMMENT ON TABLE PocketChroot IS 'PocketChroots: Which chroot belongs to which pocket of which distroarchrelease. Any given pocket of any given distroarchrelease needs a specific chroot in order to be built. This table links it all together.';
COMMENT ON COLUMN PocketChroot.distroarchrelease IS 'Which distroarchrelease this chroot applies to.';
COMMENT ON COLUMN PocketChroot.pocket IS 'Which pocket of the distroarchrelease this chroot applies to. Valid values are specified in dbschema.PackagePublishingPocket';
COMMENT ON COLUMN PocketChroot.chroot IS 'The chroot used by the pocket of the distroarchrelease.';

-- POExportRequest
COMMENT ON TABLE POExportRequest IS
'A request from a user that a PO template or a PO file be exported
asynchronously.';
COMMENT ON COLUMN POExportRequest.person IS
'The person who made the request.';
COMMENT ON COLUMN POExportRequest.potemplate IS
'The PO template being requested.';
COMMENT ON COLUMN POExportRequest.pofile IS
'The PO file being requested, or NULL.';
COMMENT ON COLUMN POExportRequest.format IS
'The format the user would like the export to be in. See the RosettaFileFormat DB schema for possible values.';

-- GPGKey
COMMENT ON TABLE GPGKey IS 'A GPG key belonging to a Person';
COMMENT ON COLUMN GPGKey.keyid IS 'The 8 character GPG key id, uppercase and no whitespace';
COMMENT ON COLUMN GPGKey.fingerprint IS 'The 40 character GPG fingerprint, uppercase and no whitespace';
COMMENT ON COLUMN GPGKey.revoked IS 'True if this key has been revoked';
COMMENT ON COLUMN GPGKey.algorithm IS 'The algorithm used to generate this key. Valid values defined in dbschema.GPGKeyAlgorithms';
COMMENT ON COLUMN GPGKey.keysize IS 'Size of the key in bits, as reported by GPG. We may refuse to deal with keysizes < 768 bits in the future.';

-- Calendar
COMMENT ON TABLE Calendar IS 'A Calendar attached to some other Launchpad object (currently People, Projects or Products)';
COMMENT ON COLUMN Calendar.title IS 'The title of the Calendar';

COMMENT ON TABLE CalendarSubscription IS 'A subscription relationship between two calendars';
COMMENT ON COLUMN CalendarSubscription.subject IS 'The subject of the subscription relationship';
COMMENT ON COLUMN CalendarSubscription.object IS 'The object of the subscription relationship';
COMMENT ON COLUMN CalendarSubscription.colour IS 'The colour used to display events from calendar \'object\' when in the context of calendar \'subject\'';

COMMENT ON TABLE CalendarEvent IS 'Events belonging to calendars';
COMMENT ON COLUMN CalendarEvent.uid IS 'A globally unique identifier for the event.  This identifier should be preserved through when importing events from a desktop calendar application';
COMMENT ON COLUMN CalendarEvent.calendar IS 'The calendar this event belongs to';
COMMENT ON COLUMN CalendarEvent.startdate IS 'The start time for the event in UTC';
COMMENT ON COLUMN CalendarEvent.duration IS 'The duration of the event';
COMMENT ON COLUMN CalendarEvent.title IS 'A one line description of the event';
COMMENT ON COLUMN CalendarEvent.description IS 'A multiline description of the event';
COMMENT ON COLUMN CalendarEvent.location IS 'A location associated with the event';
