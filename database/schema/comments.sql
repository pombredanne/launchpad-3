/*
  Add Comments to Launchpad database
*/

-- Project
COMMENT ON TABLE Project IS 'Project: A DOAP Project. This table is the core of the DOAP section of the Launchpad database. It contains details of a single open source Project and is the anchor point for products, potemplates, and translationefforts.';
COMMENT ON COLUMN Project.owner IS 'The owner of the project will initially be the person who creates this Project in the system. We will encourage upstream project leaders to take on this role. The Project owner is able to edit the project and appoint project administrators (administrators are recorded in the ProjectRole table).';
COMMENT ON COLUMN Project.homepageurl IS 'The home page URL of this project. Note that this could well be the home page of the main product of this project as well, if the project is too small to have a separate home page for project and product.';
COMMENT ON COLUMN Project.wikiurl IS 'This is the URL of a wiki that includes information about the project. It might be a page in a bigger wiki, or it might be the top page of a wiki devoted to this project.';
COMMENT ON COLUMN Project.lastdoap IS 'This column stores a cached copy of the last DOAP description we saw for this project. We cache the last DOAP fragment for this project because there may be some aspects of it which we are unable to represent in the database (such as multiple homepageurl\'s instead of just a single homepageurl) and storing the DOAP file allows us to re-parse it later and recover this information when our database model has been updated appropriately.';
COMMENT ON COLUMN Project.name IS 'A short lowercase name uniquely identifying the product. Use cases include being used as a key in URL traversal.';
COMMENT ON COLUMN Project.sourceforgeproject IS 'The SourceForge project name for this project. This is not unique as SourceForge doesn\'t use the same project/product structure as DOAP.';
COMMENT ON COLUMN Project.freshmeatproject IS 'The FreshMeat project name for this project. This is not unique as FreshMeat does not have the same project/product structure as DOAP';


-- ProjectRelationship
COMMENT ON TABLE ProjectRelationship IS 'Project Relationships. This table stores information about the way projects are related to one another in the open source world. The actual nature of the relationship is stored in the \'label\' field, and possible values are given by the ProjectRelationship enum in dbschema.py. Examples are AGGREGATES ("the Gnome Project AGGREGATES EOG and Evolution and Gnumeric and AbiWord") and SIMILAR ("the Evolution project is SIMILAR to the Mutt project").';
COMMENT ON COLUMN ProjectRelationship.subject IS 'The subject of the relationship. Relationships are generally unidirectional - A AGGREGATES B is not the same as B AGGREGATES A. In the example "Gnome AGGREGATES Evolution", Gnome is the subject.';
COMMENT ON COLUMN ProjectRelationship.object IS 'The object of the relationship. In the example "Gnome AGGREGATES Evolution", Evolution is the object.';
COMMENT ON COLUMN ProjectRelationship.label IS 'The nature of the relationship. This integer takes one of the values enumerated in dbschema.py ProjectRelationship';

-- EmailAddress
COMMENT ON COLUMN EmailAddress.email IS 'An email address used by a Person. The email address is stored in a casesensitive way, but must be case insensitivly unique.';

-- ProjectRole
COMMENT ON TABLE ProjectRole IS 'Project Roles. This table records the explicit roles that people play in an open source project, with the exception of the \'ownership\' role, which is encoded in Project.owner. Types of roles are enumerated in dbschema.py DOAPRole.';
COMMENT ON COLUMN ProjectRole.person IS 'The person playing the role.';
COMMENT ON COLUMN ProjectRole.role IS 'The role, an integer enumeration documented in dbschema.py ProjectRole.';
COMMENT ON COLUMN ProjectRole.project IS 'The project in which the person plays a role.';


-- Product
COMMENT ON TABLE Product IS 'Product: a DOAP Product. This table stores core information about an open source product. In Launchpad, anything that can be shipped as a tarball would be a product, and in some cases there might be products for things that never actually ship, depending on the project. For example, most projects will have a \'website\' product, because that allows you to file a Malone bug against the project website. Note that these are not actual product releases, which are stored in the ProductRelease table.';
COMMENT ON COLUMN Product.owner IS 'The Product owner would typically be the person who createed this product in Launchpad. But we will encourage the upstream maintainer of a product to become the owner in Launchpad. The Product owner can edit any aspect of the Product, as well as appointing people to specific roles with regard to the Product (see the ProductRole table). Also, the owner can add a new ProductRelease and also edit Rosetta POTemplates associated with this product.';
COMMENT ON COLUMN Product.project IS 'Every Product belongs to one and only one Project, which is referenced in this column.';
COMMENT ON COLUMN Product.listurl IS 'This is the URL where information about a mailing list for this Product can be found. The URL might point at a web archive or at the page where one can subscribe to the mailing list.';
COMMENT ON COLUMN Product.programminglang IS 'This field records, in plain text, the name of any significant programming languages used in this product. There are no rules, conventions or restrictions on this field at present, other than basic sanity. Examples might be "Python", "Python, C" and "Java".';
COMMENT ON COLUMN Product.downloadurl IS 'The download URL for a Product should be the best place to download that product, typically off the relevant Project web site. This should not point at the actual file, but at a web page with download information.';
COMMENT ON COLUMN Product.lastdoap IS 'This column stores a cached copy of the last DOAP description we saw for this product. See the Project.lastdoap field for more info.';
-- COMMENT ON COLUMN Product.manifest IS 'The Product manifest, if it exists, tells us exactly which branches are combined to make up the source of this product. Manifests are a Sourcerer invention, mainly used for distribution packaging, but they can apply equally well to an upstream Product. If a manifest exists for this product then this field points to it.';
COMMENT ON COLUMN Product.sourceforgeproject IS 'The SourceForge project name for this product. This is not unique as SourceForge doesn\'t use the same project/product structure as DOAP.';
COMMENT ON COLUMN Product.freshmeatproject IS 'The FreshMeat project name for this product. This is not unique as FreshMeat does not have the same project/product structure as DOAP';



-- ProductLabel
COMMENT ON TABLE ProductLabel IS 'The Product label table. We have not yet clearly defined the nature of product labels, so please do not refer to this table yet. If you have a need for tags or labels on Products, please contact Mark.';



-- ProductRole
COMMENT ON TABLE ProductRole IS 'Product Roles: this table documents the roles that people play with regard to a specific product. Note that if the project only has one product then it\'s best to document these roles at the project level, not at the product level. If a project has many products, then this table allows you to identify people playing a role that is specific to one of them.';
COMMENT ON COLUMN ProductRole.person IS 'The person playing the role.';
COMMENT ON COLUMN ProductRole.role IS 'The role being played. Valid roles are documented in dbschema.py DOAPRole. The roles are exactly the same as those used for ProjectRole.';
COMMENT ON COLUMN ProductRole.product IS 'The product where the person plays this role.';



-- ProductSeries
COMMENT ON TABLE ProductSeries IS 'A ProductSeries is a set of product releases that are related to a specific version of the product. Typically, each major release of the product starts a new ProductSeries. These often map to a branch in the revision control system of the project, such as "2_0_STABLE". A few conventional Series names are "head" for releases of the HEAD branch, "1.0" for releases with version numbers like "1.0.0" and "1.0.1".';
COMMENT ON COLUMN ProductSeries.name IS 'The name of the ProductSeries is like a unix name, it should not contain any spaces and should start with a letter or number. Good examples are "2.0", "3.0", "head" and "development".';
COMMENT ON COLUMN ProductSeries.shortdesc IS 'A short description of this Product Series. A good example would include the date the series was initiated and whether this is the current recommended series for people to use.';



-- ProductRelease
COMMENT ON TABLE ProductRelease IS 'A Product Release. This is table stores information about a specific \'upstream\' software release, like Apache 2.0.49 or Evolution 1.5.4.';
COMMENT ON COLUMN ProductRelease.version IS 'This is a text field containing the version string for this release, such as \'1.2.4\' or \'2.0.38\' or \'7.4.3\'.';
COMMENT ON COLUMN ProductRelease.title IS 'This is the GSV Name of this release, like \'The Warty Warthog Release\' or \'All your base-0 are belong to us\'. Many upstream projects are assigning fun names to their releases - these go in this field.';
COMMENT ON COLUMN ProductRelease.shortdesc IS 'A short description of this ProductRelease. This should be a very brief overview of changes and highlights, just a short paragraph of text.';
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


/*
  Buttress
*/



/*
  Malone
*/
COMMENT ON COLUMN Bug.name IS 
    'A lowercase name uniquely identifying the bug';


/*
  Soyuz
*/
-- Are these soyuz or butress?
COMMENT ON COLUMN SourcePackage.sourcepackagename IS 
    'A lowercase name identifying the sourcepackage';
COMMENT ON COLUMN SourcePackageName.name IS
    'A lowercase name identifying one or more sourcepackages';
COMMENT ON COLUMN BinaryPackageName.name IS
    'A lowercase name identifying one or more binarypackages';
COMMENT ON COLUMN SourcePackage.srcpackageformat IS 
    'The format of this source package, e.g. DPKG, RPM, EBUILD, etc.';


/* Lucille's configuration */

COMMENT ON COLUMN distribution.lucilleconfig IS 'Configuration
information which lucille will use when processing uploads and
generating archives for this distribution';

COMMENT ON COLUMN distrorelease.lucilleconfig IS 'Configuration
information which lucille will use when processing uploads and
generating archives for this distro release';


COMMENT ON COLUMN ArchArchive.name IS 'The archive name, usually in the format of an email address';


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

-- PersonLanguage
COMMENT ON TABLE PersonLanguage IS 'PersonLanguage: This table stores the preferred languages that a Person has, it''s used in Rosetta to select the languages that should be showed to be translated.';
COMMENT ON COLUMN PersonLanguage.person IS 'This field is a reference to a Person object that has this preference.';
COMMENT ON COLUMN PersonLanguage.language IS 'This field is a reference to a Language object that says that the Person associated to this row knows how to translate/understand this language.';
