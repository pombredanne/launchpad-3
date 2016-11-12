# Copyright 2009-2016 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Update the interface schema values due to circular imports.

There are situations where there would normally be circular imports to define
the necessary schema values in some interface fields.  To avoid this the
schema is initially set to `Interface`, but this needs to be updated once the
types are defined.
"""

__metaclass__ = type


__all__ = []


from lazr.restful.fields import Reference

from lp.blueprints.interfaces.specification import ISpecification
from lp.blueprints.interfaces.specificationbranch import ISpecificationBranch
from lp.blueprints.interfaces.specificationtarget import (
    IHasSpecifications,
    ISpecificationTarget,
    )
from lp.bugs.interfaces.bug import (
    IBug,
    IFrontPageBugAddForm,
    )
from lp.bugs.interfaces.bugactivity import IBugActivity
from lp.bugs.interfaces.bugattachment import IBugAttachment
from lp.bugs.interfaces.bugbranch import IBugBranch
from lp.bugs.interfaces.bugnomination import IBugNomination
from lp.bugs.interfaces.bugsubscriptionfilter import IBugSubscriptionFilter
from lp.bugs.interfaces.bugtarget import (
    IBugTarget,
    IHasBugs,
    )
from lp.bugs.interfaces.bugtask import IBugTask
from lp.bugs.interfaces.bugtracker import (
    IBugTracker,
    IBugTrackerComponent,
    IBugTrackerComponentGroup,
    IBugTrackerSet,
    )
from lp.bugs.interfaces.bugwatch import IBugWatch
from lp.bugs.interfaces.cve import ICve
from lp.bugs.interfaces.malone import IMaloneApplication
from lp.bugs.interfaces.structuralsubscription import (
    IStructuralSubscription,
    IStructuralSubscriptionTarget,
    )
from lp.buildmaster.interfaces.builder import (
    IBuilder,
    IBuilderSet,
    )
from lp.buildmaster.interfaces.buildfarmjob import IBuildFarmJob
from lp.buildmaster.interfaces.buildqueue import IBuildQueue
from lp.code.interfaces.branch import (
    IBranch,
    IBranchSet,
    )
from lp.code.interfaces.branchmergeproposal import IBranchMergeProposal
from lp.code.interfaces.branchsubscription import IBranchSubscription
from lp.code.interfaces.codeimport import ICodeImport
from lp.code.interfaces.codereviewcomment import ICodeReviewComment
from lp.code.interfaces.codereviewvote import ICodeReviewVoteReference
from lp.code.interfaces.diff import IPreviewDiff
from lp.code.interfaces.gitref import IGitRef
from lp.code.interfaces.gitrepository import IGitRepository
from lp.code.interfaces.gitsubscription import IGitSubscription
from lp.code.interfaces.hasbranches import (
    IHasBranches,
    IHasCodeImports,
    IHasMergeProposals,
    IHasRequestedReviews,
    )
from lp.code.interfaces.hasrecipes import IHasRecipes
from lp.code.interfaces.sourcepackagerecipe import ISourcePackageRecipe
from lp.code.interfaces.sourcepackagerecipebuild import (
    ISourcePackageRecipeBuild,
    )
from lp.hardwaredb.interfaces.hwdb import (
    HWBus,
    IHWDBApplication,
    IHWDevice,
    IHWDeviceClass,
    IHWDriver,
    IHWDriverName,
    IHWDriverPackageName,
    IHWSubmission,
    IHWSubmissionDevice,
    IHWVendorID,
    )
from lp.registry.interfaces.commercialsubscription import (
    ICommercialSubscription,
    )
from lp.registry.interfaces.distribution import IDistribution
from lp.registry.interfaces.distributionmirror import IDistributionMirror
from lp.registry.interfaces.distributionsourcepackage import (
    IDistributionSourcePackage,
    )
from lp.registry.interfaces.distroseries import IDistroSeries
from lp.registry.interfaces.distroseriesdifference import (
    IDistroSeriesDifference,
    )
from lp.registry.interfaces.distroseriesdifferencecomment import (
    IDistroSeriesDifferenceComment,
    )
from lp.registry.interfaces.gpg import IGPGKey
from lp.registry.interfaces.irc import IIrcID
from lp.registry.interfaces.jabber import IJabberID
from lp.registry.interfaces.milestone import (
    IHasMilestones,
    IMilestone,
    )
from lp.registry.interfaces.person import (
    IPerson,
    IPersonEditRestricted,
    IPersonLimitedView,
    IPersonViewRestricted,
    ITeam,
    )
from lp.registry.interfaces.pillar import (
    IPillar,
    IPillarNameSet,
    )
from lp.registry.interfaces.pocket import PackagePublishingPocket
from lp.registry.interfaces.product import (
    IProduct,
    IProductSet,
    )
from lp.registry.interfaces.productrelease import (
    IProductRelease,
    IProductReleaseFile,
    )
from lp.registry.interfaces.productseries import (
    IProductSeries,
    ITimelineProductSeries,
    )
from lp.registry.interfaces.projectgroup import (
    IProjectGroup,
    IProjectGroupSet,
    )
from lp.registry.interfaces.sourcepackage import (
    ISourcePackage,
    ISourcePackageEdit,
    ISourcePackagePublic,
    )
from lp.registry.interfaces.ssh import ISSHKey
from lp.registry.interfaces.teammembership import ITeamMembership
from lp.registry.interfaces.wikiname import IWikiName
from lp.services.comments.interfaces.conversation import IComment
from lp.services.messages.interfaces.message import (
    IIndexedMessage,
    IMessage,
    IUserToUserEmail,
    )
from lp.services.webservice.apihelpers import (
    patch_choice_parameter_type,
    patch_choice_property,
    patch_collection_property,
    patch_collection_return_type,
    patch_entry_explicit_version,
    patch_entry_return_type,
    patch_list_parameter_type,
    patch_operations_explicit_version,
    patch_plain_parameter_type,
    patch_reference_property,
    )
from lp.services.worlddata.interfaces.country import (
    ICountry,
    ICountrySet,
    )
from lp.services.worlddata.interfaces.language import (
    ILanguage,
    ILanguageSet,
    )
from lp.soyuz.interfaces.archive import IArchive
from lp.soyuz.interfaces.archivedependency import IArchiveDependency
from lp.soyuz.interfaces.archivepermission import IArchivePermission
from lp.soyuz.interfaces.archivesubscriber import IArchiveSubscriber
from lp.soyuz.interfaces.binarypackagebuild import IBinaryPackageBuild
from lp.soyuz.interfaces.binarypackagerelease import (
    IBinaryPackageReleaseDownloadCount,
    )
from lp.soyuz.interfaces.buildrecords import IHasBuildRecords
from lp.soyuz.interfaces.distroarchseries import IDistroArchSeries
from lp.soyuz.interfaces.livefs import ILiveFSView
from lp.soyuz.interfaces.livefsbuild import (
    ILiveFSBuild,
    ILiveFSFile,
    )
from lp.soyuz.interfaces.packageset import (
    IPackageset,
    IPackagesetSet,
    )
from lp.soyuz.interfaces.publishing import (
    IBinaryPackagePublishingHistory,
    IBinaryPackagePublishingHistoryEdit,
    ISourcePackagePublishingHistory,
    ISourcePackagePublishingHistoryEdit,
    ISourcePackagePublishingHistoryPublic,
    )
from lp.soyuz.interfaces.queue import IPackageUpload
from lp.soyuz.interfaces.sourcepackagerelease import ISourcePackageRelease
from lp.translations.interfaces.hastranslationimports import (
    IHasTranslationImports,
    )
from lp.translations.interfaces.hastranslationtemplates import (
    IHasTranslationTemplates,
    )
from lp.translations.interfaces.pofile import IPOFile
from lp.translations.interfaces.potemplate import (
    IPOTemplate,
    IPOTemplateSharingSubset,
    IPOTemplateSubset,
    )
from lp.translations.interfaces.translationgroup import ITranslationGroup
from lp.translations.interfaces.translationimportqueue import (
    ITranslationImportQueue,
    ITranslationImportQueueEntry,
    )


patch_collection_property(IBranch, 'bug_branches', IBugBranch)
patch_collection_property(IBranch, 'linked_bugs', IBug)
patch_collection_property(IBranch, 'dependent_branches', IBranchMergeProposal)
patch_entry_return_type(IBranch, 'getSubscription', IBranchSubscription)
patch_collection_property(
    IBranch, '_api_landing_candidates', IBranchMergeProposal)
patch_collection_property(IBranch, 'landing_targets', IBranchMergeProposal)
patch_plain_parameter_type(IBranch, 'linkBug', 'bug', IBug)
patch_plain_parameter_type(
    IBranch, 'linkSpecification', 'spec', ISpecification)
patch_reference_property(IBranch, 'product', IProduct)

patch_plain_parameter_type(IBranch, 'setTarget', 'project', IProduct)
patch_plain_parameter_type(
    IBranch, 'setTarget', 'source_package', ISourcePackage)
patch_reference_property(IBranch, 'sourcepackage', ISourcePackage)
patch_reference_property(IBranch, 'code_import', ICodeImport)

patch_collection_property(IBranch, 'spec_links', ISpecificationBranch)
patch_entry_return_type(IBranch, 'subscribe', IBranchSubscription)
patch_collection_property(IBranch, 'subscriptions', IBranchSubscription)
patch_plain_parameter_type(IBranch, 'unlinkBug', 'bug', IBug)
patch_plain_parameter_type(
    IBranch, 'unlinkSpecification', 'spec', ISpecification)

patch_entry_return_type(IBranch, '_createMergeProposal', IBranchMergeProposal)
patch_plain_parameter_type(
    IBranch, '_createMergeProposal', 'merge_target', IBranch)
patch_plain_parameter_type(
    IBranch, '_createMergeProposal', 'merge_prerequisite', IBranch)
patch_collection_return_type(
    IBranch, 'getMergeProposals', IBranchMergeProposal)

patch_collection_return_type(
    IBranchSet, 'getMergeProposals', IBranchMergeProposal)

patch_entry_return_type(IBranchMergeProposal, 'getComment', ICodeReviewComment)
patch_plain_parameter_type(
    IBranchMergeProposal, 'createComment', 'parent', ICodeReviewComment)
patch_entry_return_type(
    IBranchMergeProposal, 'createComment', ICodeReviewComment)
patch_collection_property(
    IBranchMergeProposal, 'all_comments', ICodeReviewComment)
patch_entry_return_type(
    IBranchMergeProposal, 'nominateReviewer', ICodeReviewVoteReference)
patch_collection_property(
    IBranchMergeProposal, 'votes', ICodeReviewVoteReference)
patch_collection_return_type(
    IBranchMergeProposal, 'getRelatedBugTasks', IBugTask)
patch_plain_parameter_type(IBranchMergeProposal, 'linkBug', 'bug', IBug)
patch_plain_parameter_type(IBranchMergeProposal, 'unlinkBug', 'bug', IBug)

patch_collection_return_type(IHasBranches, 'getBranches', IBranch)
patch_collection_return_type(
    IHasMergeProposals, 'getMergeProposals', IBranchMergeProposal)
patch_collection_return_type(
    IHasRequestedReviews, 'getRequestedReviews', IBranchMergeProposal)
patch_entry_return_type(IHasCodeImports, 'newCodeImport', ICodeImport)
patch_plain_parameter_type(IHasCodeImports, 'newCodeImport', 'owner', IPerson)

# IBugTask

patch_collection_return_type(IBugTask, 'findSimilarBugs', IBug)
patch_plain_parameter_type(
    IBug, 'linkHWSubmission', 'submission', IHWSubmission)
patch_plain_parameter_type(
    IBug, 'unlinkHWSubmission', 'submission', IHWSubmission)
patch_collection_return_type(IBug, 'getHWSubmissions', IHWSubmission)
patch_list_parameter_type(
    IBug, 'getNominations', 'nominations', Reference(schema=IBugNomination))
patch_entry_return_type(IBug, 'addNomination', IBugNomination)
patch_entry_return_type(IBug, 'getNominationFor', IBugNomination)
patch_collection_return_type(IBug, 'getNominations', IBugNomination)

patch_choice_parameter_type(IHasBugs, 'searchTasks', 'hardware_bus', HWBus)

patch_reference_property(
    IPreviewDiff, 'branch_merge_proposal', IBranchMergeProposal)

patch_reference_property(IPersonViewRestricted, 'archive', IArchive)
patch_collection_property(IPersonViewRestricted, 'ppas', IArchive)
patch_plain_parameter_type(
    IPersonLimitedView, 'getPPAByName', 'distribution', IDistribution)
patch_entry_return_type(IPersonLimitedView, 'getPPAByName', IArchive)
patch_plain_parameter_type(
    IPersonEditRestricted, 'createPPA', 'distribution', IDistribution)
patch_entry_return_type(IPersonEditRestricted, 'createPPA', IArchive)

patch_choice_parameter_type(
    IHasBuildRecords, 'getBuildRecords', 'pocket', PackagePublishingPocket)
patch_collection_return_type(
    IHasBuildRecords, 'getBuildRecords', IBinaryPackageBuild)

patch_reference_property(ISourcePackagePublic, 'distroseries', IDistroSeries)
patch_reference_property(ISourcePackagePublic, 'productseries', IProductSeries)
patch_choice_parameter_type(
    ISourcePackagePublic, 'getBranch', 'pocket', PackagePublishingPocket)
patch_entry_return_type(ISourcePackagePublic, 'getBranch', IBranch)
patch_choice_parameter_type(
    ISourcePackageEdit, 'setBranch', 'pocket', PackagePublishingPocket)
patch_plain_parameter_type(ISourcePackageEdit, 'setBranch', 'branch', IBranch)
patch_reference_property(ISourcePackage, 'distribution', IDistribution)

# IPerson
patch_entry_return_type(IPerson, 'createRecipe', ISourcePackageRecipe)
patch_list_parameter_type(IPerson, 'createRecipe', 'distroseries',
                          Reference(schema=IDistroSeries))
patch_plain_parameter_type(IPerson, 'createRecipe', 'daily_build_archive',
                           IArchive)
patch_plain_parameter_type(IPerson, 'getArchiveSubscriptionURL', 'archive',
                           IArchive)
patch_collection_return_type(
    IPerson, 'getArchiveSubscriptions', IArchiveSubscriber)
patch_entry_return_type(IPerson, 'getRecipe', ISourcePackageRecipe)
patch_collection_return_type(IPerson, 'getOwnedProjects', IProduct)

# IHasRecipe
patch_collection_property(IHasRecipes, 'recipes', ISourcePackageRecipe)

patch_collection_property(IPerson, 'hardware_submissions', IHWSubmission)

# publishing.py
patch_collection_return_type(
    ISourcePackagePublishingHistoryPublic, 'getBuilds', IBinaryPackageBuild)
patch_collection_return_type(
    ISourcePackagePublishingHistoryPublic, 'getPublishedBinaries',
    IBinaryPackagePublishingHistory)
patch_reference_property(
    IBinaryPackagePublishingHistory, 'distroarchseries',
    IDistroArchSeries)
patch_reference_property(
    IBinaryPackagePublishingHistory, 'build', IBinaryPackageBuild)
patch_reference_property(
    IBinaryPackagePublishingHistory, 'archive', IArchive)
patch_reference_property(
    ISourcePackagePublishingHistory, 'archive', IArchive)
patch_reference_property(
    ISourcePackagePublishingHistory, 'ancestor',
    ISourcePackagePublishingHistory)
patch_reference_property(
    ISourcePackagePublishingHistory, 'packageupload', IPackageUpload)
patch_entry_return_type(
    ISourcePackagePublishingHistoryEdit, 'changeOverride',
    ISourcePackagePublishingHistory)
patch_entry_return_type(
    IBinaryPackagePublishingHistoryEdit, 'changeOverride',
    IBinaryPackagePublishingHistory)

# IArchive apocalypse.
patch_reference_property(IArchive, 'distribution', IDistribution)
patch_collection_property(IArchive, 'dependencies', IArchiveDependency)
patch_collection_return_type(IArchive, 'getAllPermissions', IArchivePermission)
patch_collection_return_type(
    IArchive, 'getPermissionsForPerson', IArchivePermission)
patch_collection_return_type(
    IArchive, 'getUploadersForPackage', IArchivePermission)
patch_collection_return_type(
    IArchive, 'getUploadersForPackageset', IArchivePermission)
patch_collection_return_type(
    IArchive, 'getPackagesetsForUploader', IArchivePermission)
patch_collection_return_type(
    IArchive, 'getPackagesetsForSourceUploader', IArchivePermission)
patch_collection_return_type(
    IArchive, 'getPackagesetsForSource', IArchivePermission)
patch_collection_return_type(
    IArchive, 'getUploadersForComponent', IArchivePermission)
patch_collection_return_type(
    IArchive, 'getQueueAdminsForComponent', IArchivePermission)
patch_collection_return_type(
    IArchive, 'getComponentsForQueueAdmin', IArchivePermission)
patch_collection_return_type(
    IArchive, 'getQueueAdminsForPocket', IArchivePermission)
patch_collection_return_type(
    IArchive, 'getPocketsForQueueAdmin', IArchivePermission)
patch_collection_return_type(
    IArchive, 'getPocketsForUploader', IArchivePermission)
patch_collection_return_type(
    IArchive, 'getUploadersForPocket', IArchivePermission)
patch_entry_return_type(IArchive, 'newPackageUploader', IArchivePermission)
patch_entry_return_type(IArchive, 'newPackagesetUploader', IArchivePermission)
patch_entry_return_type(IArchive, 'newComponentUploader', IArchivePermission)
patch_entry_return_type(IArchive, 'newPocketUploader', IArchivePermission)
patch_entry_return_type(IArchive, 'newQueueAdmin', IArchivePermission)
patch_entry_return_type(IArchive, 'newPocketQueueAdmin', IArchivePermission)
patch_plain_parameter_type(IArchive, 'syncSources', 'from_archive', IArchive)
patch_plain_parameter_type(IArchive, 'syncSource', 'from_archive', IArchive)
patch_plain_parameter_type(IArchive, 'copyPackage', 'from_archive', IArchive)
patch_plain_parameter_type(
    IArchive, 'copyPackages', 'from_archive', IArchive)
patch_entry_return_type(IArchive, 'newSubscription', IArchiveSubscriber)
patch_plain_parameter_type(
    IArchive, 'getArchiveDependency', 'dependency', IArchive)
patch_entry_return_type(IArchive, 'getArchiveDependency', IArchiveDependency)
patch_plain_parameter_type(
    IArchive, 'api_getPublishedSources', 'distroseries', IDistroSeries)
patch_collection_return_type(
    IArchive, 'api_getPublishedSources', ISourcePackagePublishingHistory)
patch_choice_parameter_type(
    IArchive, 'api_getPublishedSources', 'pocket', PackagePublishingPocket)
patch_plain_parameter_type(
    IArchive, 'getAllPublishedBinaries', 'distroarchseries',
    IDistroArchSeries)
patch_collection_return_type(
    IArchive, 'getAllPublishedBinaries', IBinaryPackagePublishingHistory)
patch_choice_parameter_type(
    IArchive, 'getAllPublishedBinaries', 'pocket', PackagePublishingPocket)
patch_plain_parameter_type(
    IArchive, 'isSourceUploadAllowed', 'distroseries', IDistroSeries)
patch_plain_parameter_type(
    IArchive, '_checkUpload', 'distroseries', IDistroSeries)
patch_choice_parameter_type(
    IArchive, '_checkUpload', 'pocket', PackagePublishingPocket)
patch_choice_parameter_type(
    IArchive, 'getUploadersForPocket', 'pocket', PackagePublishingPocket)
patch_choice_parameter_type(
    IArchive, 'getQueueAdminsForPocket', 'pocket', PackagePublishingPocket)
patch_plain_parameter_type(
    IArchive, 'getQueueAdminsForPocket', 'distroseries', IDistroSeries)
patch_choice_parameter_type(
    IArchive, 'newPocketUploader', 'pocket', PackagePublishingPocket)
patch_choice_parameter_type(
    IArchive, 'newPocketQueueAdmin', 'pocket', PackagePublishingPocket)
patch_plain_parameter_type(
    IArchive, 'newPocketQueueAdmin', 'distroseries', IDistroSeries)
patch_choice_parameter_type(
    IArchive, 'deletePocketUploader', 'pocket', PackagePublishingPocket)
patch_choice_parameter_type(
    IArchive, 'deletePocketQueueAdmin', 'pocket', PackagePublishingPocket)
patch_plain_parameter_type(
    IArchive, 'deletePocketQueueAdmin', 'distroseries', IDistroSeries)
patch_plain_parameter_type(
    IArchive, 'newPackagesetUploader', 'packageset', IPackageset)
patch_plain_parameter_type(
    IArchive, 'getUploadersForPackageset', 'packageset', IPackageset)
patch_plain_parameter_type(
    IArchive, 'deletePackagesetUploader', 'packageset', IPackageset)
patch_plain_parameter_type(
    IArchive, 'removeArchiveDependency', 'dependency', IArchive)
patch_plain_parameter_type(
    IArchive, '_addArchiveDependency', 'dependency', IArchive)
patch_choice_parameter_type(
    IArchive, '_addArchiveDependency', 'pocket', PackagePublishingPocket)
patch_entry_return_type(
    IArchive, '_addArchiveDependency', IArchiveDependency)

# IBuildFarmJob
patch_reference_property(IBuildFarmJob, 'buildqueue_record', IBuildQueue)

# IComment
patch_reference_property(IComment, 'comment_author', IPerson)

# IDistribution
patch_collection_property(IDistribution, 'series', IDistroSeries)
patch_collection_property(IDistribution, 'derivatives', IDistroSeries)
patch_reference_property(IDistribution, 'currentseries', IDistroSeries)
patch_entry_return_type(IDistribution, 'getArchive', IArchive)
patch_entry_return_type(IDistribution, 'getSeries', IDistroSeries)
patch_collection_return_type(
    IDistribution, 'getDevelopmentSeries', IDistroSeries)
patch_entry_return_type(
    IDistribution, 'getSourcePackage', IDistributionSourcePackage)
patch_collection_return_type(
    IDistribution, 'searchSourcePackages', IDistributionSourcePackage)
patch_reference_property(IDistribution, 'main_archive', IArchive)
patch_collection_property(IDistribution, 'all_distro_archives', IArchive)


# IDistributionMirror
patch_reference_property(IDistributionMirror, 'distribution', IDistribution)


# IDistroSeries
patch_entry_return_type(
    IDistroSeries, 'getDistroArchSeries', IDistroArchSeries)
patch_reference_property(IDistroSeries, 'main_archive', IArchive)
patch_collection_property(
    IDistroSeries, 'enabled_architectures', IDistroArchSeries)
patch_reference_property(IDistroSeries, 'distribution', IDistribution)
patch_choice_parameter_type(
    IDistroSeries, 'getPackageUploads', 'pocket', PackagePublishingPocket)
patch_plain_parameter_type(
    IDistroSeries, 'getPackageUploads', 'archive', IArchive)
patch_collection_return_type(
    IDistroSeries, 'getPackageUploads', IPackageUpload)
patch_reference_property(IDistroSeries, 'previous_series', IDistroSeries)
patch_reference_property(
    IDistroSeries, 'nominatedarchindep', IDistroArchSeries)
patch_collection_return_type(IDistroSeries, 'getDerivedSeries', IDistroSeries)
patch_collection_return_type(IDistroSeries, 'getParentSeries', IDistroSeries)
patch_plain_parameter_type(
    IDistroSeries, 'getDifferencesTo', 'parent_series', IDistroSeries)
patch_collection_return_type(
    IDistroSeries, 'getDifferencesTo', IDistroSeriesDifference)
patch_collection_return_type(
    IDistroSeries, 'getDifferenceComments', IDistroSeriesDifferenceComment)


# IDistroSeriesDifference
patch_reference_property(
    IDistroSeriesDifference, 'latest_comment', IDistroSeriesDifferenceComment)

# IDistroSeriesDifferenceComment
patch_reference_property(
    IDistroSeriesDifferenceComment, 'comment_author', IPerson)

# IDistroArchSeries
patch_reference_property(IDistroArchSeries, 'main_archive', IArchive)

# IGitRef
patch_reference_property(IGitRef, 'repository', IGitRepository)
patch_plain_parameter_type(
    IGitRef, 'createMergeProposal', 'merge_target', IGitRef)
patch_plain_parameter_type(
    IGitRef, 'createMergeProposal', 'merge_prerequisite', IGitRef)
patch_collection_property(IGitRef, 'landing_targets', IBranchMergeProposal)
patch_collection_property(IGitRef, 'landing_candidates', IBranchMergeProposal)
patch_collection_property(IGitRef, 'dependent_landings', IBranchMergeProposal)
patch_entry_return_type(IGitRef, 'createMergeProposal', IBranchMergeProposal)
patch_collection_return_type(
    IGitRef, 'getMergeProposals', IBranchMergeProposal)

# IGitRepository
patch_collection_property(IGitRepository, 'branches', IGitRef)
patch_collection_property(IGitRepository, 'refs', IGitRef)
patch_collection_property(IGitRepository, 'subscriptions', IGitSubscription)
patch_entry_return_type(IGitRepository, 'subscribe', IGitSubscription)
patch_entry_return_type(IGitRepository, 'getSubscription', IGitSubscription)
patch_reference_property(IGitRepository, 'code_import', ICodeImport)
patch_collection_property(
    IGitRepository, 'landing_targets', IBranchMergeProposal)
patch_collection_property(
    IGitRepository, 'landing_candidates', IBranchMergeProposal)
patch_collection_property(
    IGitRepository, 'dependent_landings', IBranchMergeProposal)

# ILiveFSFile
patch_reference_property(ILiveFSFile, 'livefsbuild', ILiveFSBuild)

# ILiveFSView
patch_entry_return_type(ILiveFSView, 'requestBuild', ILiveFSBuild)
patch_collection_property(ILiveFSView, 'builds', ILiveFSBuild)
patch_collection_property(ILiveFSView, 'completed_builds', ILiveFSBuild)
patch_collection_property(ILiveFSView, 'pending_builds', ILiveFSBuild)

# IPackageset
patch_collection_return_type(IPackageset, 'setsIncluded', IPackageset)
patch_collection_return_type(IPackageset, 'setsIncludedBy', IPackageset)
patch_plain_parameter_type(
    IPackageset, 'getSourcesSharedBy', 'other_package_set', IPackageset)
patch_plain_parameter_type(
    IPackageset, 'getSourcesNotSharedBy', 'other_package_set', IPackageset)
patch_collection_return_type(IPackageset, 'relatedSets', IPackageset)

# IPackageUpload
patch_choice_property(IPackageUpload, 'pocket', PackagePublishingPocket)
patch_reference_property(IPackageUpload, 'distroseries', IDistroSeries)
patch_reference_property(IPackageUpload, 'archive', IArchive)
patch_reference_property(IPackageUpload, 'copy_source_archive', IArchive)

# IStructuralSubscription
patch_collection_property(
    IStructuralSubscription, 'bug_filters', IBugSubscriptionFilter)
patch_entry_return_type(
    IStructuralSubscription, "newBugFilter", IBugSubscriptionFilter)
patch_reference_property(
    IStructuralSubscription, 'target', IStructuralSubscriptionTarget)

# IStructuralSubscriptionTarget
patch_reference_property(
    IStructuralSubscriptionTarget, 'parent_subscription_target',
    IStructuralSubscriptionTarget)
patch_entry_return_type(
    IStructuralSubscriptionTarget, 'addBugSubscriptionFilter',
    IBugSubscriptionFilter)

# ISourcePackageRelease
patch_reference_property(
    ISourcePackageRelease, 'source_package_recipe_build',
    ISourcePackageRecipeBuild)

# ISourcePackageRecipeView
patch_entry_return_type(
    ISourcePackageRecipe, 'requestBuild', ISourcePackageRecipeBuild)
patch_reference_property(
    ISourcePackageRecipe, 'last_build', ISourcePackageRecipeBuild)
patch_collection_property(
    ISourcePackageRecipe, 'builds', ISourcePackageRecipeBuild)
patch_collection_property(
    ISourcePackageRecipe, 'pending_builds', ISourcePackageRecipeBuild)
patch_collection_property(
    ISourcePackageRecipe, 'completed_builds', ISourcePackageRecipeBuild)

# IHasBugs
patch_plain_parameter_type(IHasBugs, 'searchTasks', 'assignee', IPerson)
patch_plain_parameter_type(IHasBugs, 'searchTasks', 'bug_reporter', IPerson)
patch_plain_parameter_type(IHasBugs, 'searchTasks', 'bug_supervisor', IPerson)
patch_plain_parameter_type(IHasBugs, 'searchTasks', 'bug_commenter', IPerson)
patch_plain_parameter_type(IHasBugs, 'searchTasks', 'bug_subscriber', IPerson)
patch_plain_parameter_type(IHasBugs, 'searchTasks', 'owner', IPerson)
patch_plain_parameter_type(IHasBugs, 'searchTasks', 'affected_user', IPerson)
patch_plain_parameter_type(
    IHasBugs, 'searchTasks', 'structural_subscriber', IPerson)

# IBugTask
patch_reference_property(IBugTask, 'owner', IPerson)

# IBugWatch
patch_reference_property(IBugWatch, 'owner', IPerson)

# IHasTranslationImports
patch_collection_return_type(
    IHasTranslationImports, 'getTranslationImportQueueEntries',
    ITranslationImportQueueEntry)

# IIndexedMessage
patch_reference_property(IIndexedMessage, 'inside', IBugTask)

# IMessage
patch_reference_property(IMessage, 'owner', IPerson)

# IUserToUserEmail
patch_reference_property(IUserToUserEmail, 'sender', IPerson)
patch_reference_property(IUserToUserEmail, 'recipient', IPerson)

# IBug
patch_plain_parameter_type(
    IBug, 'addNomination', 'target', IBugTarget)
patch_plain_parameter_type(
    IBug, 'canBeNominatedFor', 'target', IBugTarget)
patch_plain_parameter_type(
    IBug, 'getNominationFor', 'target', IBugTarget)
patch_plain_parameter_type(
    IBug, 'getNominations', 'target', IBugTarget)
patch_collection_property(IBug, 'linked_merge_proposals', IBranchMergeProposal)
patch_plain_parameter_type(
    IBug, 'linkMergeProposal', 'merge_proposal', IBranchMergeProposal)
patch_plain_parameter_type(
    IBug, 'unlinkMergeProposal', 'merge_proposal', IBranchMergeProposal)


# IFrontPageBugAddForm
patch_reference_property(IFrontPageBugAddForm, 'bugtarget', IBugTarget)

# IBugTracker
patch_reference_property(IBugTracker, 'owner', IPerson)
patch_entry_return_type(
    IBugTracker, 'getRemoteComponentGroup', IBugTrackerComponentGroup)
patch_entry_return_type(
    IBugTracker, 'addRemoteComponentGroup', IBugTrackerComponentGroup)
patch_collection_return_type(
    IBugTracker, 'getAllRemoteComponentGroups', IBugTrackerComponentGroup)
patch_entry_return_type(
    IBugTracker, 'getRemoteComponentForDistroSourcePackageName',
    IBugTrackerComponent)

## IBugTrackerComponent
patch_reference_property(
    IBugTrackerComponent, "distro_source_package",
    IDistributionSourcePackage)

# IHasTranslationTemplates
patch_collection_return_type(
    IHasTranslationTemplates, 'getTranslationTemplates', IPOTemplate)

# IPOTemplate
patch_collection_property(IPOTemplate, 'pofiles', IPOFile)
patch_reference_property(IPOTemplate, 'product', IProduct)

# IPOTemplateSubset
patch_reference_property(IPOTemplateSubset, 'distroseries', IDistroSeries)
patch_reference_property(IPOTemplateSubset, 'productseries', IProductSeries)

# IPOTemplateSharingSubset
patch_reference_property(IPOTemplateSharingSubset, 'product', IProduct)

# IPerson
patch_collection_return_type(
    IPerson, 'getBugSubscriberPackages', IDistributionSourcePackage)

# IProductSeries
patch_reference_property(IProductSeries, 'product', IProduct)

# ISpecification
patch_plain_parameter_type(ISpecification, 'linkBug', 'bug', IBug)
patch_plain_parameter_type(ISpecification, 'unlinkBug', 'bug', IBug)
patch_collection_property(ISpecification, 'dependencies', ISpecification)
patch_collection_property(
    ISpecification, 'linked_branches', ISpecificationBranch)

# ISpecificationTarget
patch_entry_return_type(
    ISpecificationTarget, 'getSpecification', ISpecification)

# IHasSpecifications
patch_collection_property(
    IHasSpecifications, 'visible_specifications', ISpecification)
patch_collection_property(
    IHasSpecifications, 'api_valid_specifications', ISpecification)


###
#
# Our web service configuration requires that every entry, field, and
# named operation explicitly name the version in which it first
# appears. This code grandfathers in entries and named operations that
# were defined before this rule came into effect. When you change an
# interface in the future, you should add explicit version statements to
# its definition and get rid of the patch calls here.
#
###

# IArchive
patch_entry_explicit_version(IArchive, 'beta')
patch_operations_explicit_version(
    IArchive, 'beta', "_checkUpload", "deleteComponentUploader",
    "deletePackageUploader", "deletePackagesetUploader", "deleteQueueAdmin",
    "getAllPublishedBinaries", "getArchiveDependency", "getBuildCounters",
    "getBuildSummariesForSourceIds", "getComponentsForQueueAdmin",
    "getPackagesetsForSource", "getPackagesetsForSourceUploader",
    "getPackagesetsForUploader", "getPermissionsForPerson",
    "api_getPublishedSources", "getQueueAdminsForComponent",
    "getUploadersForComponent", "getUploadersForPackage",
    "getUploadersForPackageset", "isSourceUploadAllowed",
    "newComponentUploader", "newPackageUploader", "newPackagesetUploader",
    "newQueueAdmin", "newSubscription", "syncSource", "syncSources")

# IArchiveDependency
patch_entry_explicit_version(IArchiveDependency, 'beta')

# IArchivePermission
patch_entry_explicit_version(IArchivePermission, 'beta')

# IArchiveSubscriber
patch_entry_explicit_version(IArchiveSubscriber, 'beta')

# IBinaryPackageBuild
patch_entry_explicit_version(IBinaryPackageBuild, 'beta')
patch_operations_explicit_version(
    IBinaryPackageBuild, 'beta', "rescore", "retry")

# IBinaryPackagePublishingHistory
patch_entry_explicit_version(IBinaryPackagePublishingHistory, 'beta')
patch_operations_explicit_version(
    IBinaryPackagePublishingHistory, 'beta', "getDailyDownloadTotals",
    "getDownloadCount", "getDownloadCounts")

# IBinaryPackageReleaseDownloadCount
patch_entry_explicit_version(IBinaryPackageReleaseDownloadCount, 'beta')

# IBranch
patch_entry_explicit_version(IBranch, 'beta')

# IBranchMergeProposal
patch_entry_explicit_version(IBranchMergeProposal, 'beta')
patch_operations_explicit_version(
    IBranchMergeProposal, 'beta', "createComment", "getComment",
    "nominateReviewer", "setStatus")

# IBranchSubscription
patch_entry_explicit_version(IBranchSubscription, 'beta')
patch_operations_explicit_version(
    IBranchSubscription, 'beta', "canBeUnsubscribedByUser")

# IBug
patch_entry_explicit_version(IBug, 'beta')
patch_operations_explicit_version(
    IBug, 'beta', "addAttachment", "addNomination", "addTask", "addWatch",
    "canBeNominatedFor", "getHWSubmissions", "getNominationFor",
    "getNominations", "isExpirable", "isUserAffected",
    "linkCVE", "linkHWSubmission", "markAsDuplicate",
    "markUserAffected", "newMessage", "setCommentVisibility", "setPrivate",
    "setSecurityRelated", "subscribe", "unlinkCVE", "unlinkHWSubmission",
    "unsubscribe", "unsubscribeFromDupes")

# IBugActivity
patch_entry_explicit_version(IBugActivity, 'beta')

# IBugAttachment
patch_entry_explicit_version(IBugAttachment, 'beta')
patch_operations_explicit_version(
    IBugAttachment, 'beta', "removeFromBug")

# IBugBranch
patch_entry_explicit_version(IBugBranch, 'beta')

# IBugNomination
patch_entry_explicit_version(IBugNomination, 'beta')
patch_operations_explicit_version(
    IBugNomination, 'beta', "approve", "canApprove", "decline")

# IBugSubscriptionFilter
patch_entry_explicit_version(IBugSubscriptionFilter, 'beta')
patch_operations_explicit_version(
    IBugSubscriptionFilter, 'beta', "delete")

# IBugTarget
patch_entry_explicit_version(IBugTarget, 'beta')

# IBugTask
patch_entry_explicit_version(IBugTask, 'beta')
patch_operations_explicit_version(
    IBugTask, 'beta', "findSimilarBugs", "transitionToAssignee",
    "transitionToImportance", "transitionToMilestone", "transitionToStatus",
    "transitionToTarget")

# IBugTracker
patch_entry_explicit_version(IBugTracker, 'beta')
patch_operations_explicit_version(
    IBugTracker, 'beta', "addRemoteComponentGroup",
    "getAllRemoteComponentGroups", "getRemoteComponentGroup")

# IBugTrackerComponent
patch_entry_explicit_version(IBugTrackerComponent, 'beta')

# IBugTrackerComponentGroup
patch_entry_explicit_version(IBugTrackerComponentGroup, 'beta')
patch_operations_explicit_version(
    IBugTrackerComponentGroup, 'beta', "addComponent")

# IBugTrackerSet
patch_operations_explicit_version(
    IBugTrackerSet, 'beta', "ensureBugTracker", "getByName", "queryByBaseURL")

# IBugWatch
patch_entry_explicit_version(IBugWatch, 'beta')

# IBuilder
patch_entry_explicit_version(IBuilder, 'beta')
patch_reference_property(IBuilder, 'current_build', IBuildFarmJob)

# IBuilderSet
patch_operations_explicit_version(IBuilderSet, 'beta', "getByName")

# ICodeImport
patch_entry_explicit_version(ICodeImport, 'beta')
patch_operations_explicit_version(
    ICodeImport, 'beta', "requestImport")

# ICodeReviewComment
patch_entry_explicit_version(ICodeReviewComment, 'beta')

# ICodeReviewVoteReference
patch_entry_explicit_version(ICodeReviewVoteReference, 'beta')
patch_operations_explicit_version(
    ICodeReviewVoteReference, 'beta', "claimReview", "delete",
    "reassignReview")

# ICommercialSubscription
patch_entry_explicit_version(ICommercialSubscription, 'beta')

# ICountry
patch_entry_explicit_version(ICountry, 'beta')

# ICountrySet
patch_operations_explicit_version(
    ICountrySet, 'beta', "getByCode", "getByName")

# ICve
patch_entry_explicit_version(ICve, 'beta')

# IDistribution
patch_operations_explicit_version(
    IDistribution, 'beta', "getArchive", "getCountryMirror",
    "getDevelopmentSeries", "getMirrorByName", "getSeries",
    "getSourcePackage", "searchSourcePackages")

# IDistributionMirror
patch_entry_explicit_version(IDistributionMirror, 'beta')
patch_operations_explicit_version(
    IDistributionMirror, 'beta', "canTransitionToCountryMirror",
    "getOverallFreshness", "isOfficial", "transitionToCountryMirror")

# IDistributionSourcePackage
patch_entry_explicit_version(IDistributionSourcePackage, 'beta')

# IDistroArchSeries
patch_entry_explicit_version(IDistroArchSeries, 'beta')

# IDistroSeries
patch_entry_explicit_version(IDistroSeries, 'beta')
patch_operations_explicit_version(
    IDistroSeries, 'beta', "initDerivedDistroSeries", "getDerivedSeries",
    "getParentSeries", "getDistroArchSeries", "getPackageUploads",
    "getSourcePackage", "newMilestone")

# IDistroSeriesDifference
patch_entry_explicit_version(IDistroSeriesDifference, 'beta')
patch_operations_explicit_version(
    IDistroSeriesDifference, 'beta', "addComment", "blacklist",
    "requestPackageDiffs", "unblacklist")

# IDistroSeriesDifferenceComment
patch_entry_explicit_version(IDistroSeriesDifferenceComment, 'beta')

# IGPGKey
patch_entry_explicit_version(IGPGKey, 'beta')

# IHWDBApplication
patch_entry_explicit_version(IHWDBApplication, 'beta')
patch_operations_explicit_version(
    IHWDBApplication, 'beta', "deviceDriverOwnersAffectedByBugs", "devices",
    "drivers", "hwInfoByBugRelatedUsers", "numDevicesInSubmissions",
    "numOwnersOfDevice", "numSubmissionsWithDevice", "search", "vendorIDs")

# IHWDevice
patch_entry_explicit_version(IHWDevice, 'beta')
patch_operations_explicit_version(
    IHWDevice, 'beta', "getOrCreateDeviceClass", "getSubmissions",
    "removeDeviceClass")

# IHWDeviceClass
patch_entry_explicit_version(IHWDeviceClass, 'beta')
patch_operations_explicit_version(
    IHWDeviceClass, 'beta', "delete")

# IHWDriver
patch_entry_explicit_version(IHWDriver, 'beta')
patch_operations_explicit_version(
    IHWDriver, 'beta', "getSubmissions")

# IHWDriverName
patch_entry_explicit_version(IHWDriverName, 'beta')

# IHWDriverPackageName
patch_entry_explicit_version(IHWDriverPackageName, 'beta')

# IHWSubmission
patch_entry_explicit_version(IHWSubmission, 'beta')

# IHWSubmissionDevice
patch_entry_explicit_version(IHWSubmissionDevice, 'beta')

# IHWVendorID
patch_entry_explicit_version(IHWVendorID, 'beta')

# IHasBugs
patch_entry_explicit_version(IHasBugs, 'beta')

# IHasMilestones
patch_entry_explicit_version(IHasMilestones, 'beta')

# IHasTranslationImports
patch_entry_explicit_version(IHasTranslationImports, 'beta')

# IIrcID
patch_entry_explicit_version(IIrcID, 'beta')

# IJabberID
patch_entry_explicit_version(IJabberID, 'beta')

# ILanguage
patch_entry_explicit_version(ILanguage, 'beta')

# ILanguageSet
patch_operations_explicit_version(ILanguageSet, 'beta', "getAllLanguages")

# IMaloneApplication
patch_operations_explicit_version(IMaloneApplication, 'beta', "createBug")

# IMessage
patch_entry_explicit_version(IMessage, 'beta')

# IMilestone
patch_entry_explicit_version(IMilestone, 'beta')

# IPOFile
patch_entry_explicit_version(IPOFile, 'beta')

# IPOTemplate
patch_entry_explicit_version(IPOTemplate, 'beta')

# IPackageUpload
patch_entry_explicit_version(IPackageUpload, 'beta')

# IPackageset
patch_entry_explicit_version(IPackageset, 'beta')
patch_operations_explicit_version(
    IPackageset, 'beta', "addSources", "addSubsets", "getSourcesIncluded",
    "getSourcesNotSharedBy", "getSourcesSharedBy", "relatedSets",
    "removeSources", "removeSubsets", "setsIncluded", "setsIncludedBy")

# IPackagesetSet
patch_operations_explicit_version(
    IPackagesetSet, 'beta', "getByName", "new", "setsIncludingSource")

# IPerson
patch_entry_explicit_version(IPerson, 'beta')

# IPillar
patch_entry_explicit_version(IPillar, 'beta')

# IPillarNameSet
patch_entry_explicit_version(IPillarNameSet, 'beta')
patch_operations_explicit_version(
    IPillarNameSet, 'beta', "search")

# IPreviewDiff
patch_entry_explicit_version(IPreviewDiff, 'beta')

# IProduct
patch_entry_explicit_version(IProduct, 'beta')
patch_operations_explicit_version(
    IProduct, 'beta', "getRelease", "getSeries", "getTimeline", "newSeries")

# IProductRelease
patch_entry_explicit_version(IProductRelease, 'beta')
patch_operations_explicit_version(
    IProductRelease, 'beta', "addReleaseFile", "destroySelf")

# IProductReleaseFile
patch_entry_explicit_version(IProductReleaseFile, 'beta')
patch_operations_explicit_version(
    IProductReleaseFile, 'beta', "destroySelf")

# IProductSeries
patch_entry_explicit_version(IProductSeries, 'beta')
patch_operations_explicit_version(
    IProductSeries, 'beta', "getTimeline", "newMilestone")

# IProductSet
patch_operations_explicit_version(
    IProductSet, 'beta', "createProduct", "forReview", "latest", "search")

# IProjectGroup
patch_entry_explicit_version(IProjectGroup, 'beta')

# IProjectGroupSet
patch_operations_explicit_version(
    IProjectGroupSet, 'beta', "search")

# ISSHKey
patch_entry_explicit_version(ISSHKey, 'beta')

# ISourcePackage
patch_entry_explicit_version(ISourcePackage, 'beta')
patch_operations_explicit_version(
    ISourcePackage, 'beta', "getBranch", "linkedBranches", "setBranch")

# ISourcePackagePublishingHistory
patch_entry_explicit_version(ISourcePackagePublishingHistory, 'beta')
patch_operations_explicit_version(
    ISourcePackagePublishingHistory, 'beta', "api_requestDeletion",
    "binaryFileUrls", "changesFileUrl", "getBuilds", "getPublishedBinaries",
    "packageDiffUrl", "sourceFileUrls")

# ISourcePackageRecipe
patch_entry_explicit_version(ISourcePackageRecipe, 'beta')
patch_operations_explicit_version(
    ISourcePackageRecipe, 'beta', "performDailyBuild", "requestBuild",
    "setRecipeText")

# ISourcePackageRecipeBuild
patch_entry_explicit_version(ISourcePackageRecipeBuild, 'beta')

# IStructuralSubscription
patch_entry_explicit_version(IStructuralSubscription, 'beta')
patch_operations_explicit_version(
    IStructuralSubscription, 'beta', "delete", "newBugFilter")

# IStructuralSubscriptionTarget
patch_entry_explicit_version(IStructuralSubscriptionTarget, 'beta')

# ITeam
patch_entry_explicit_version(ITeam, 'beta')

# ITeamMembership
patch_entry_explicit_version(ITeamMembership, 'beta')
patch_operations_explicit_version(
    ITeamMembership, 'beta', "setExpirationDate", "setStatus")

# ITimelineProductSeries
patch_entry_explicit_version(ITimelineProductSeries, 'beta')

# ITranslationGroup
patch_entry_explicit_version(ITranslationGroup, 'beta')

# ITranslationImportQueue
patch_operations_explicit_version(
    ITranslationImportQueue, 'beta', "getAllEntries", "getFirstEntryToImport",
    "getRequestTargets")

# ITranslationImportQueueEntry
patch_entry_explicit_version(ITranslationImportQueueEntry, 'beta')
patch_operations_explicit_version(
    ITranslationImportQueueEntry, 'beta', "setStatus")

# IWikiName
patch_entry_explicit_version(IWikiName, 'beta')
