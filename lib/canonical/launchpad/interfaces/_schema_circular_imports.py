# Copyright 2009-2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Update the interface schema values due to circular imports.

There are situations where there would normally be circular imports to define
the necessary schema values in some interface fields.  To avoid this the
schema is initially set to `Interface`, but this needs to be updated once the
types are defined.
"""

__metaclass__ = type


__all__ = []


from lazr.restful.declarations import LAZR_WEBSERVICE_EXPORTED
from lazr.restful.fields import Reference

from canonical.launchpad.components.apihelpers import (
    patch_choice_parameter_type,
    patch_choice_vocabulary,
    patch_collection_property,
    patch_collection_return_type,
    patch_entry_explicit_version,
    patch_entry_return_type,
    patch_list_parameter_type,
    patch_operation_explicit_version,
    patch_plain_parameter_type,
    patch_reference_property,
    )
from canonical.launchpad.interfaces.message import (
    IIndexedMessage,
    IMessage,
    IUserToUserEmail,
    )
from lp.blueprints.interfaces.specification import ISpecification
from lp.blueprints.interfaces.specificationbranch import ISpecificationBranch
from lp.blueprints.interfaces.specificationtarget import (
    IHasSpecifications,
    ISpecificationTarget,
    )
from lp.bugs.enum import BugNotificationLevel
from lp.bugs.interfaces.bug import (
    IBug,
    IFrontPageBugAddForm,
    )
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
    )
from lp.bugs.interfaces.bugwatch import IBugWatch
from lp.buildmaster.enums import BuildStatus
from lp.buildmaster.interfaces.buildfarmjob import IBuildFarmJob
from lp.buildmaster.interfaces.buildqueue import IBuildQueue
from lp.code.interfaces.branch import IBranch
from lp.code.interfaces.branchmergeproposal import IBranchMergeProposal
from lp.code.interfaces.branchsubscription import IBranchSubscription
from lp.code.interfaces.codeimport import ICodeImport
from lp.code.interfaces.codereviewcomment import ICodeReviewComment
from lp.code.interfaces.codereviewvote import ICodeReviewVoteReference
from lp.code.interfaces.diff import IPreviewDiff
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
    IHWSubmission,
    )
from lp.registry.interfaces.distribution import IDistribution
from lp.registry.interfaces.distributionmirror import IDistributionMirror
from lp.registry.interfaces.distributionsourcepackage import (
    IDistributionSourcePackage,
    )
from lp.registry.interfaces.distroseries import IDistroSeries
from lp.registry.interfaces.distroseriesdifferencecomment import (
    IDistroSeriesDifferenceComment,
    )
from lp.registry.interfaces.person import (
    IPerson,
    IPersonPublic,
    )
from lp.registry.interfaces.pocket import PackagePublishingPocket
from lp.registry.interfaces.product import IProduct
from lp.registry.interfaces.productseries import IProductSeries
from lp.registry.interfaces.sourcepackage import ISourcePackage
from lp.bugs.interfaces.structuralsubscription import (
    IStructuralSubscription,
    IStructuralSubscriptionTarget,
    )
from lp.services.comments.interfaces.conversation import IComment
from lp.soyuz.enums import (
    PackagePublishingStatus,
    PackageUploadCustomFormat,
    PackageUploadStatus,
    )
from lp.soyuz.interfaces.archive import IArchive
from lp.soyuz.interfaces.archivedependency import IArchiveDependency
from lp.soyuz.interfaces.archivepermission import IArchivePermission
from lp.soyuz.interfaces.archivesubscriber import IArchiveSubscriber
from lp.soyuz.interfaces.binarypackagebuild import IBinaryPackageBuild
from lp.soyuz.interfaces.buildrecords import IHasBuildRecords
from lp.soyuz.interfaces.distroarchseries import IDistroArchSeries
from lp.soyuz.interfaces.packageset import IPackageset
from lp.soyuz.interfaces.publishing import (
    IBinaryPackagePublishingHistory,
    ISourcePackagePublishingHistory,
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
from lp.translations.interfaces.translationimportqueue import (
    ITranslationImportQueueEntry,
    )


IBranch['bug_branches'].value_type.schema = IBugBranch
IBranch['linked_bugs'].value_type.schema = IBug
IBranch['dependent_branches'].value_type.schema = IBranchMergeProposal
IBranch['getSubscription'].queryTaggedValue(
    LAZR_WEBSERVICE_EXPORTED)['return_type'].schema = IBranchSubscription
IBranch['landing_candidates'].value_type.schema = IBranchMergeProposal
IBranch['landing_targets'].value_type.schema = IBranchMergeProposal
IBranch['linkBug'].queryTaggedValue(
    LAZR_WEBSERVICE_EXPORTED)['params']['bug'].schema= IBug
IBranch['linkSpecification'].queryTaggedValue(
    LAZR_WEBSERVICE_EXPORTED)['params']['spec'].schema= ISpecification
IBranch['product'].schema = IProduct

patch_plain_parameter_type(
    IBranch, 'setTarget', 'project', IProduct)
patch_plain_parameter_type(
    IBranch, 'setTarget', 'source_package', ISourcePackage)
patch_reference_property(IBranch, 'sourcepackage', ISourcePackage)
patch_reference_property(IBranch, 'code_import', ICodeImport)

IBranch['spec_links'].value_type.schema = ISpecificationBranch
IBranch['subscribe'].queryTaggedValue(
    LAZR_WEBSERVICE_EXPORTED)['return_type'].schema = IBranchSubscription
IBranch['subscriptions'].value_type.schema = IBranchSubscription
IBranch['unlinkBug'].queryTaggedValue(
    LAZR_WEBSERVICE_EXPORTED)['params']['bug'].schema= IBug
IBranch['unlinkSpecification'].queryTaggedValue(
    LAZR_WEBSERVICE_EXPORTED)['params']['spec'].schema= ISpecification

patch_entry_return_type(IBranch, '_createMergeProposal', IBranchMergeProposal)
patch_plain_parameter_type(
    IBranch, '_createMergeProposal', 'target_branch', IBranch)
patch_plain_parameter_type(
    IBranch, '_createMergeProposal', 'prerequisite_branch', IBranch)
patch_collection_return_type(
    IBranch, 'getMergeProposals', IBranchMergeProposal)

IBranchMergeProposal['getComment'].queryTaggedValue(
    LAZR_WEBSERVICE_EXPORTED)['return_type'].schema = ICodeReviewComment
IBranchMergeProposal['createComment'].queryTaggedValue(
    LAZR_WEBSERVICE_EXPORTED)['params']['parent'].schema = \
        ICodeReviewComment
patch_entry_return_type(
    IBranchMergeProposal, 'createComment', ICodeReviewComment)
IBranchMergeProposal['all_comments'].value_type.schema = ICodeReviewComment
IBranchMergeProposal['nominateReviewer'].queryTaggedValue(
    LAZR_WEBSERVICE_EXPORTED)['return_type'].schema = ICodeReviewVoteReference
IBranchMergeProposal['votes'].value_type.schema = ICodeReviewVoteReference
patch_collection_return_type(
    IBranchMergeProposal, 'getRelatedBugTasks', IBugTask)

patch_collection_return_type(IHasBranches, 'getBranches', IBranch)
patch_collection_return_type(
    IHasMergeProposals, 'getMergeProposals', IBranchMergeProposal)
patch_collection_return_type(
    IHasRequestedReviews, 'getRequestedReviews', IBranchMergeProposal)
patch_entry_return_type(
    IHasCodeImports, 'newCodeImport', ICodeImport)
patch_plain_parameter_type(
    IHasCodeImports, 'newCodeImport', 'owner', IPerson)

# IBugTask

IBugTask['findSimilarBugs'].queryTaggedValue(
    LAZR_WEBSERVICE_EXPORTED)['return_type'].value_type.schema = IBug
patch_plain_parameter_type(
    IBug, 'linkHWSubmission', 'submission', IHWSubmission)
patch_plain_parameter_type(
    IBug, 'unlinkHWSubmission', 'submission', IHWSubmission)
patch_collection_return_type(
    IBug, 'getHWSubmissions', IHWSubmission)
IBug['getNominations'].queryTaggedValue(
    LAZR_WEBSERVICE_EXPORTED)['params']['nominations'].value_type.schema = (
        IBugNomination)
patch_entry_return_type(IBug, 'addNomination', IBugNomination)
patch_entry_return_type(IBug, 'getNominationFor', IBugNomination)
patch_collection_return_type(IBug, 'getNominations', IBugNomination)

patch_choice_parameter_type(
    IHasBugs, 'searchTasks', 'hardware_bus', HWBus)

IPreviewDiff['branch_merge_proposal'].schema = IBranchMergeProposal

patch_reference_property(IPersonPublic, 'archive', IArchive)
patch_collection_property(IPersonPublic, 'ppas', IArchive)
patch_entry_return_type(IPersonPublic, 'getPPAByName', IArchive)
patch_entry_return_type(IPersonPublic, 'createPPA', IArchive)

IHasBuildRecords['getBuildRecords'].queryTaggedValue(
    LAZR_WEBSERVICE_EXPORTED)[
        'params']['pocket'].vocabulary = PackagePublishingPocket
IHasBuildRecords['getBuildRecords'].queryTaggedValue(
    LAZR_WEBSERVICE_EXPORTED)[
        'params']['build_state'].vocabulary = BuildStatus
IHasBuildRecords['getBuildRecords'].queryTaggedValue(
    LAZR_WEBSERVICE_EXPORTED)[
        'return_type'].value_type.schema = IBinaryPackageBuild

ISourcePackage['distroseries'].schema = IDistroSeries
ISourcePackage['productseries'].schema = IProductSeries
ISourcePackage['getBranch'].queryTaggedValue(
    LAZR_WEBSERVICE_EXPORTED)[
        'params']['pocket'].vocabulary = PackagePublishingPocket
ISourcePackage['getBranch'].queryTaggedValue(
    LAZR_WEBSERVICE_EXPORTED)['return_type'].schema = IBranch
ISourcePackage['setBranch'].queryTaggedValue(
    LAZR_WEBSERVICE_EXPORTED)[
        'params']['pocket'].vocabulary = PackagePublishingPocket
ISourcePackage['setBranch'].queryTaggedValue(
    LAZR_WEBSERVICE_EXPORTED)['params']['branch'].schema = IBranch
patch_reference_property(ISourcePackage, 'distribution', IDistribution)

# IPerson
patch_entry_return_type(IPerson, 'createRecipe', ISourcePackageRecipe)
patch_list_parameter_type(IPerson, 'createRecipe', 'distroseries',
                          Reference(schema=IDistroSeries))
patch_plain_parameter_type(IPerson, 'createRecipe', 'daily_build_archive',
                           IArchive)
patch_plain_parameter_type(IPerson, 'getArchiveSubscriptionURL', 'archive',
                           IArchive)

patch_entry_return_type(IPerson, 'getRecipe', ISourcePackageRecipe)

# IHasRecipe
patch_collection_property(
    IHasRecipes, 'recipes', ISourcePackageRecipe)

IPerson['hardware_submissions'].value_type.schema = IHWSubmission

# publishing.py
ISourcePackagePublishingHistoryPublic['getBuilds'].queryTaggedValue(
    LAZR_WEBSERVICE_EXPORTED)['return_type'].value_type.schema = (
        IBinaryPackageBuild)
ISourcePackagePublishingHistoryPublic[
    'getPublishedBinaries'].queryTaggedValue(
        LAZR_WEBSERVICE_EXPORTED)[
            'return_type'].value_type.schema = IBinaryPackagePublishingHistory
patch_reference_property(
    IBinaryPackagePublishingHistory, 'distroarchseries',
    IDistroArchSeries)
patch_reference_property(
    IBinaryPackagePublishingHistory, 'archive', IArchive)
patch_reference_property(
    ISourcePackagePublishingHistory, 'archive', IArchive)
patch_reference_property(
    ISourcePackagePublishingHistory, 'ancestor',
    ISourcePackagePublishingHistory)

# IArchive apocalypse.
patch_reference_property(IArchive, 'distribution', IDistribution)
patch_collection_property(IArchive, 'dependencies', IArchiveDependency)
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
patch_entry_return_type(IArchive, 'newPackageUploader', IArchivePermission)
patch_entry_return_type(IArchive, 'newPackagesetUploader', IArchivePermission)
patch_entry_return_type(IArchive, 'newComponentUploader', IArchivePermission)
patch_entry_return_type(IArchive, 'newQueueAdmin', IArchivePermission)
patch_plain_parameter_type(IArchive, 'syncSources', 'from_archive', IArchive)
patch_plain_parameter_type(IArchive, 'syncSource', 'from_archive', IArchive)
patch_entry_return_type(IArchive, 'newSubscription', IArchiveSubscriber)
patch_plain_parameter_type(
    IArchive, 'getArchiveDependency', 'dependency', IArchive)
patch_entry_return_type(IArchive, 'getArchiveDependency', IArchiveDependency)
patch_plain_parameter_type(
    IArchive, 'getPublishedSources', 'distroseries', IDistroSeries)
patch_collection_return_type(
    IArchive, 'getPublishedSources', ISourcePackagePublishingHistory)
patch_choice_parameter_type(
    IArchive, 'getPublishedSources', 'status', PackagePublishingStatus)
patch_choice_parameter_type(
    IArchive, 'getPublishedSources', 'pocket', PackagePublishingPocket)
patch_plain_parameter_type(
    IArchive, 'getAllPublishedBinaries', 'distroarchseries',
    IDistroArchSeries)
patch_collection_return_type(
    IArchive, 'getAllPublishedBinaries', IBinaryPackagePublishingHistory)
patch_choice_parameter_type(
    IArchive, 'getAllPublishedBinaries', 'status', PackagePublishingStatus)
patch_choice_parameter_type(
    IArchive, 'getAllPublishedBinaries', 'pocket', PackagePublishingPocket)
patch_plain_parameter_type(
    IArchive, 'isSourceUploadAllowed', 'distroseries', IDistroSeries)
patch_plain_parameter_type(
    IArchive, '_checkUpload', 'distroseries', IDistroSeries)
patch_choice_parameter_type(
    IArchive, '_checkUpload', 'pocket', PackagePublishingPocket)
patch_plain_parameter_type(
    IArchive, 'newPackagesetUploader', 'packageset', IPackageset)
patch_plain_parameter_type(
    IArchive, 'getUploadersForPackageset', 'packageset', IPackageset)
patch_plain_parameter_type(
    IArchive, 'deletePackagesetUploader', 'packageset', IPackageset)


# IBuildFarmJob
IBuildFarmJob['status'].vocabulary = BuildStatus
IBuildFarmJob['buildqueue_record'].schema = IBuildQueue

# IComment
IComment['comment_author'].schema = IPerson

# IDistribution
IDistribution['series'].value_type.schema = IDistroSeries
patch_reference_property(
    IDistribution, 'currentseries', IDistroSeries)
patch_entry_return_type(
    IDistribution, 'getArchive', IArchive)
patch_entry_return_type(
    IDistribution, 'getSeries', IDistroSeries)
patch_collection_return_type(
    IDistribution, 'getDevelopmentSeries', IDistroSeries)
patch_entry_return_type(
    IDistribution, 'getSourcePackage', IDistributionSourcePackage)
patch_collection_return_type(
    IDistribution, 'searchSourcePackages', IDistributionSourcePackage)
patch_collection_return_type(
    IDistribution, 'getCommercialPPAs', IArchive)
patch_reference_property(
    IDistribution, 'main_archive', IArchive)
IDistribution['all_distro_archives'].value_type.schema = IArchive


# IDistributionMirror
IDistributionMirror['distribution'].schema = IDistribution


# IDistroSeries
patch_entry_return_type(
    IDistroSeries, 'getDistroArchSeries', IDistroArchSeries)
patch_reference_property(
    IDistroSeries, 'main_archive', IArchive)
patch_reference_property(
    IDistroSeries, 'distribution', IDistribution)
patch_choice_parameter_type(
    IDistroSeries, 'getPackageUploads', 'status', PackageUploadStatus)
patch_choice_parameter_type(
    IDistroSeries, 'getPackageUploads', 'pocket', PackagePublishingPocket)
patch_choice_parameter_type(
    IDistroSeries, 'getPackageUploads', 'custom_type',
    PackageUploadCustomFormat)
patch_plain_parameter_type(
    IDistroSeries, 'getPackageUploads', 'archive', IArchive)
patch_collection_return_type(
    IDistroSeries, 'getPackageUploads', IPackageUpload)
patch_reference_property(IDistroSeries, 'parent_series', IDistroSeries)
patch_plain_parameter_type(
    IDistroSeries, 'deriveDistroSeries', 'distribution', IDistribution)
patch_collection_return_type(
    IDistroSeries, 'getDerivedSeries', IDistroSeries)


# IDistroSeriesDifferenceComment
IDistroSeriesDifferenceComment['comment_author'].schema = IPerson

# IDistroArchSeries
patch_reference_property(IDistroArchSeries, 'main_archive', IArchive)

# IPackageset
patch_collection_return_type(
    IPackageset, 'setsIncluded', IPackageset)
patch_collection_return_type(
    IPackageset, 'setsIncludedBy', IPackageset)
patch_plain_parameter_type(
    IPackageset, 'getSourcesSharedBy', 'other_package_set', IPackageset)
patch_plain_parameter_type(
    IPackageset, 'getSourcesNotSharedBy', 'other_package_set', IPackageset)
patch_collection_return_type(
    IPackageset, 'relatedSets', IPackageset)

# IPackageUpload
IPackageUpload['pocket'].vocabulary = PackagePublishingPocket
patch_reference_property(IPackageUpload, 'distroseries', IDistroSeries)
patch_reference_property(IPackageUpload, 'archive', IArchive)

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
patch_plain_parameter_type(
    IHasBugs, 'searchTasks', 'assignee', IPerson)
patch_plain_parameter_type(
    IHasBugs, 'searchTasks', 'bug_reporter', IPerson)
patch_plain_parameter_type(
    IHasBugs, 'searchTasks', 'bug_supervisor', IPerson)
patch_plain_parameter_type(
    IHasBugs, 'searchTasks', 'bug_commenter', IPerson)
patch_plain_parameter_type(
    IHasBugs, 'searchTasks', 'bug_subscriber', IPerson)
patch_plain_parameter_type(
    IHasBugs, 'searchTasks', 'owner', IPerson)
patch_plain_parameter_type(
    IHasBugs, 'searchTasks', 'affected_user', IPerson)
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
patch_choice_vocabulary(
    IBug, 'subscribe', 'level', BugNotificationLevel)


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
patch_collection_property(ISpecification, 'dependencies', ISpecification)
patch_collection_property(
    ISpecification, 'linked_branches', ISpecificationBranch)

# ISpecificationTarget
patch_entry_return_type(
    ISpecificationTarget, 'getSpecification', ISpecification)

# IHasSpecifications
patch_collection_property(
    IHasSpecifications, 'all_specifications', ISpecification)
patch_collection_property(
    IHasSpecifications, 'valid_specifications', ISpecification)


########################

from canonical.launchpad.interfaces.emailaddress import IEmailAddress
from canonical.launchpad.interfaces.message import IMessage
from canonical.launchpad.interfaces.temporaryblobstorage import (
    ITemporaryBlobStorage,
    ITemporaryStorageManager,
    )
from lp.blueprints.interfaces.specificationbranch import ISpecificationBranch
from lp.blueprints.interfaces.specification import ISpecification
from lp.blueprints.interfaces.specificationtarget import ISpecificationTarget
from lp.bugs.interfaces.bugactivity import IBugActivity
from lp.bugs.interfaces.bugattachment import IBugAttachment
from lp.bugs.interfaces.bugbranch import IBugBranch
from lp.bugs.interfaces.bug import IBug
from lp.bugs.interfaces.bugnomination import IBugNomination
from lp.bugs.interfaces.bugsubscriptionfilter import IBugSubscriptionFilter
from lp.bugs.interfaces.bugsubscription import IBugSubscription
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
from lp.bugs.interfaces.structuralsubscription import IStructuralSubscription
from lp.bugs.interfaces.structuralsubscription import IStructuralSubscriptionTarget
from lp.buildmaster.interfaces.builder import (
    IBuilder,
    IBuilderSet,
    )
from lp.code.interfaces.branch import (
    IBranch,
    IBranchSet,
    )
from lp.code.interfaces.branchmergeproposal import IBranchMergeProposal
from lp.code.interfaces.branchmergequeue import IBranchMergeQueue
from lp.code.interfaces.branchsubscription import IBranchSubscription
from lp.code.interfaces.codeimport import ICodeImport
from lp.code.interfaces.codereviewcomment import ICodeReviewComment
from lp.code.interfaces.codereviewvote import ICodeReviewVoteReference
from lp.code.interfaces.diff import IPreviewDiff
from lp.code.interfaces.sourcepackagerecipebuild import ISourcePackageRecipeBuild
from lp.code.interfaces.sourcepackagerecipe import ISourcePackageRecipe
from lp.hardwaredb.interfaces.hwdb import (
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
from lp.registry.interfaces.commercialsubscription import ICommercialSubscription
from lp.registry.interfaces.distribution import IDistribution
from lp.registry.interfaces.distributionmirror import IDistributionMirror
from lp.registry.interfaces.distributionsourcepackage import IDistributionSourcePackage
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
from lp.registry.interfaces.milestone import IHasMilestones
from lp.registry.interfaces.milestone import IMilestone
from lp.registry.interfaces.person import (
    IPerson,
    IPersonSet,
    ITeam,
    )
from lp.registry.interfaces.pillar import (
    IPillar,
    IPillarNameSet,
    )
from lp.registry.interfaces.product import (
    IProduct,
    IProductSet,
    )
from lp.registry.interfaces.productrelease import IProductRelease
from lp.registry.interfaces.productrelease import IProductReleaseFile
from lp.registry.interfaces.productseries import (
    IProductSeries,
    ITimelineProductSeries,
    )
from lp.registry.interfaces.projectgroup import (
    IProjectGroup,
    IProjectGroupSet,
    )
from lp.registry.interfaces.sourcepackage import ISourcePackage
from lp.registry.interfaces.ssh import ISSHKey
from lp.registry.interfaces.teammembership import ITeamMembership
from lp.registry.interfaces.wikiname import IWikiName
from lp.services.worlddata.interfaces.country import (
    ICountry,
    ICountrySet,
    )
from lp.services.worlddata.interfaces.language import (
    ILanguage,
    ILanguageSet,
    )
from lp.soyuz.interfaces.archivedependency import IArchiveDependency
from lp.soyuz.interfaces.archive import IArchive
from lp.soyuz.interfaces.archivepermission import IArchivePermission
from lp.soyuz.interfaces.archivesubscriber import IArchiveSubscriber
from lp.soyuz.interfaces.binarypackagebuild import IBinaryPackageBuild
from lp.soyuz.interfaces.binarypackagerelease import IBinaryPackageReleaseDownloadCount
from lp.soyuz.interfaces.distroarchseries import IDistroArchSeries
from lp.soyuz.interfaces.packageset import (
    IPackageset,
    IPackagesetSet,
    )
from lp.soyuz.interfaces.publishing import IBinaryPackagePublishingHistory
from lp.soyuz.interfaces.publishing import ISourcePackagePublishingHistory
from lp.soyuz.interfaces.queue import IPackageUpload
from lp.translations.interfaces.hastranslationimports import IHasTranslationImports
from lp.translations.interfaces.pofile import IPOFile
from lp.translations.interfaces.potemplate import IPOTemplate
from lp.translations.interfaces.translationgroup import ITranslationGroup
from lp.translations.interfaces.translationimportqueue import (
    ITranslationImportQueue,
    ITranslationImportQueueEntry,
    )

patch_entry_explicit_version(IArchive, 'beta')
patch_entry_explicit_version(IArchiveDependency, 'beta')
patch_entry_explicit_version(IArchivePermission, 'beta')
patch_entry_explicit_version(IArchiveSubscriber, 'beta')
patch_entry_explicit_version(IBinaryPackageBuild, 'beta')
patch_entry_explicit_version(IBinaryPackagePublishingHistory, 'beta')
patch_entry_explicit_version(IBinaryPackageReleaseDownloadCount, 'beta')
patch_entry_explicit_version(IBranch, 'beta')
patch_entry_explicit_version(IBranchMergeProposal, 'beta')
patch_entry_explicit_version(IBranchMergeQueue, 'beta')
patch_entry_explicit_version(IBranchSubscription, 'beta')
patch_entry_explicit_version(IBugActivity, 'beta')
patch_entry_explicit_version(IBugAttachment, 'beta')
patch_entry_explicit_version(IBug, 'beta')
patch_entry_explicit_version(IBugBranch, 'beta')
patch_entry_explicit_version(IBugNomination, 'beta')
patch_entry_explicit_version(IBugSubscriptionFilter, 'beta')
patch_entry_explicit_version(IBugTarget, 'beta')
patch_entry_explicit_version(IBugTask, 'beta')
patch_entry_explicit_version(IBugTracker, 'beta')
patch_entry_explicit_version(IBugTrackerComponent, 'beta')
patch_entry_explicit_version(IBugTrackerComponentGroup, 'beta')
patch_entry_explicit_version(IBugWatch, 'beta')
patch_entry_explicit_version(IBuilder, 'beta')
patch_entry_explicit_version(ICodeImport, 'beta')
patch_entry_explicit_version(ICodeReviewComment, 'beta')
patch_entry_explicit_version(ICodeReviewVoteReference, 'beta')
patch_entry_explicit_version(ICommercialSubscription, 'beta')
patch_entry_explicit_version(ICountry, 'beta')
patch_entry_explicit_version(ICve, 'beta')
patch_entry_explicit_version(IDistroSeries, 'beta')
patch_entry_explicit_version(IDistroSeriesDifference, 'beta')
patch_entry_explicit_version(IDistroSeriesDifferenceComment, 'beta')
patch_entry_explicit_version(IDistributionMirror, 'beta')
patch_entry_explicit_version(IDistributionSourcePackage, 'beta')
patch_entry_explicit_version(IDistroArchSeries, 'beta')
patch_entry_explicit_version(IEmailAddress, 'beta')
patch_entry_explicit_version(IGPGKey, 'beta')
patch_entry_explicit_version(IHasBugs, 'beta')
patch_entry_explicit_version(IHasMilestones, 'beta')
patch_entry_explicit_version(IHasTranslationImports, 'beta')
patch_entry_explicit_version(IHWDBApplication, 'beta')
patch_entry_explicit_version(IHWDevice, 'beta')
patch_entry_explicit_version(IHWDeviceClass, 'beta')
patch_entry_explicit_version(IHWDriver, 'beta')
patch_entry_explicit_version(IHWDriverName, 'beta')
patch_entry_explicit_version(IHWDriverPackageName, 'beta')
patch_entry_explicit_version(IHWSubmission, 'beta')
patch_entry_explicit_version(IHWSubmissionDevice, 'beta')
patch_entry_explicit_version(IHWVendorID, 'beta')
patch_entry_explicit_version(IIrcID, 'beta')
patch_entry_explicit_version(IJabberID, 'beta')
patch_entry_explicit_version(ILanguage, 'beta')
patch_entry_explicit_version(IMessage, 'beta')
patch_entry_explicit_version(IMilestone, 'beta')
patch_entry_explicit_version(IPackageset, 'beta')
patch_entry_explicit_version(IPackageUpload, 'beta')
patch_entry_explicit_version(IPerson, 'beta')
patch_entry_explicit_version(IPillar, 'beta')
patch_entry_explicit_version(IPillarNameSet, 'beta')
patch_entry_explicit_version(IPOFile, 'beta')
patch_entry_explicit_version(IPOTemplate, 'beta')
patch_entry_explicit_version(IPreviewDiff, 'beta')
patch_entry_explicit_version(IProduct, 'beta')
patch_entry_explicit_version(IProductRelease, 'beta')
patch_entry_explicit_version(IProductReleaseFile, 'beta')
patch_entry_explicit_version(IProductSeries, 'beta')
patch_entry_explicit_version(IProjectGroup, 'beta')
patch_entry_explicit_version(ISourcePackage, 'beta')
patch_entry_explicit_version(ISourcePackagePublishingHistory, 'beta')
patch_entry_explicit_version(ISourcePackageRecipe, 'beta')
patch_entry_explicit_version(ISourcePackageRecipeBuild, 'beta')
patch_entry_explicit_version(ISSHKey, 'beta')
patch_entry_explicit_version(IStructuralSubscription, 'beta')
patch_entry_explicit_version(IStructuralSubscriptionTarget, 'beta')
patch_entry_explicit_version(ITeam, 'beta')
patch_entry_explicit_version(ITeamMembership, 'beta')
patch_entry_explicit_version(ITimelineProductSeries, 'beta')
patch_entry_explicit_version(ITranslationGroup, 'beta')
patch_entry_explicit_version(ITranslationImportQueueEntry, 'beta')
patch_entry_explicit_version(IWikiName, 'beta')

patch_operation_explicit_version(IArchive, "_checkUpload", "beta")
patch_operation_explicit_version(IArchive, "deleteComponentUploader", "beta")
patch_operation_explicit_version(IArchive, "deletePackagesetUploader", "beta")
patch_operation_explicit_version(IArchive, "deletePackageUploader", "beta")
patch_operation_explicit_version(IArchive, "deleteQueueAdmin", "beta")
patch_operation_explicit_version(IArchive, "getAllPublishedBinaries", "beta")
patch_operation_explicit_version(IArchive, "getArchiveDependency", "beta")
patch_operation_explicit_version(IArchive, "getBuildCounters", "beta")
patch_operation_explicit_version(IArchive, "getBuildSummariesForSourceIds", "beta")
patch_operation_explicit_version(IArchive, "getComponentsForQueueAdmin", "beta")
patch_operation_explicit_version(IArchive, "getPackagesetsForSource", "beta")
patch_operation_explicit_version(IArchive, "getPackagesetsForSourceUploader", "beta")
patch_operation_explicit_version(IArchive, "getPackagesetsForUploader", "beta")
patch_operation_explicit_version(IArchive, "getPermissionsForPerson", "beta")
patch_operation_explicit_version(IArchive, "getPublishedSources", "beta")
patch_operation_explicit_version(IArchive, "getQueueAdminsForComponent", "beta")
patch_operation_explicit_version(IArchive, "getUploadersForComponent", "beta")
patch_operation_explicit_version(IArchive, "getUploadersForPackage", "beta")
patch_operation_explicit_version(IArchive, "getUploadersForPackageset", "beta")
patch_operation_explicit_version(IArchive, "isSourceUploadAllowed", "beta")
patch_operation_explicit_version(IArchive, "newComponentUploader", "beta")
patch_operation_explicit_version(IArchive, "newPackagesetUploader", "beta")
patch_operation_explicit_version(IArchive, "newPackageUploader", "beta")
patch_operation_explicit_version(IArchive, "newQueueAdmin", "beta")
patch_operation_explicit_version(IArchive, "newSubscription", "beta")
patch_operation_explicit_version(IArchive, "syncSource", "beta")
patch_operation_explicit_version(IArchive, "syncSources", "beta")
patch_operation_explicit_version(IBinaryPackageBuild, "rescore", "beta")
patch_operation_explicit_version(IBinaryPackageBuild, "retry", "beta")
patch_operation_explicit_version(IBinaryPackagePublishingHistory, "api_requestDeletion", "beta")
patch_operation_explicit_version(IBinaryPackagePublishingHistory, "getDailyDownloadTotals", "beta")
patch_operation_explicit_version(IBinaryPackagePublishingHistory, "getDownloadCount", "beta")
patch_operation_explicit_version(IBinaryPackagePublishingHistory, "getDownloadCounts", "beta")
patch_operation_explicit_version(IBranch, "addToQueue", "beta")
patch_operation_explicit_version(IBranch, "canBeDeleted", "beta")
patch_operation_explicit_version(IBranch, "composePublicURL", "beta")
patch_operation_explicit_version(IBranch, "_createMergeProposal", "beta")
patch_operation_explicit_version(IBranch, "destroySelfBreakReferences", "beta")
patch_operation_explicit_version(IBranch, "getMergeProposals", "beta")
patch_operation_explicit_version(IBranch, "isPersonTrustedReviewer", "beta")
patch_operation_explicit_version(IBranch, "linkBug", "beta")
patch_operation_explicit_version(IBranchMergeProposal, "createComment", "beta")
patch_operation_explicit_version(IBranchMergeProposal, "getComment", "beta")
patch_operation_explicit_version(IBranchMergeProposal, "nominateReviewer", "beta")
patch_operation_explicit_version(IBranchMergeProposal, "setStatus", "beta")
patch_operation_explicit_version(IBranchMergeProposal, "updatePreviewDiff", "beta")
patch_operation_explicit_version(IBranchMergeQueue, "setMergeQueueConfig", "beta")
patch_operation_explicit_version(IBranch, "requestMirror", "beta")
patch_operation_explicit_version(IBranchSet, "getByUniqueName", "beta")
patch_operation_explicit_version(IBranchSet, "getByUrl", "beta")
patch_operation_explicit_version(IBranchSet, "getByUrls", "beta")
patch_operation_explicit_version(IBranch, "setMergeQueueConfig", "beta")
patch_operation_explicit_version(IBranch, "setOwner", "beta")
patch_operation_explicit_version(IBranch, "setPrivate", "beta")
patch_operation_explicit_version(IBranch, "setTarget", "beta")
patch_operation_explicit_version(IBranch, "subscribe", "beta")
patch_operation_explicit_version(IBranchSubscription, "canBeUnsubscribedByUser", "beta")
patch_operation_explicit_version(IBranch, "unlinkBug", "beta")
patch_operation_explicit_version(IBranch, "unsubscribe", "beta")
patch_operation_explicit_version(IBug, "addAttachment", "beta")
patch_operation_explicit_version(IBug, "addNomination", "beta")
patch_operation_explicit_version(IBug, "addTask", "beta")
patch_operation_explicit_version(IBug, "addWatch", "beta")
patch_operation_explicit_version(IBugAttachment, "removeFromBug", "beta")
patch_operation_explicit_version(IBug, "canBeNominatedFor", "beta")
patch_operation_explicit_version(IBug, "getHWSubmissions", "beta")
patch_operation_explicit_version(IBug, "getNominationFor", "beta")
patch_operation_explicit_version(IBug, "getNominations", "beta")
patch_operation_explicit_version(IBug, "isExpirable", "beta")
patch_operation_explicit_version(IBug, "isUserAffected", "beta")
patch_operation_explicit_version(IBug, "linkBranch", "beta")
patch_operation_explicit_version(IBug, "linkCVEAndReturnNothing", "beta")
patch_operation_explicit_version(IBug, "linkHWSubmission", "beta")
patch_operation_explicit_version(IBug, "markAsDuplicate", "beta")
patch_operation_explicit_version(IBug, "markUserAffected", "beta")
patch_operation_explicit_version(IBug, "newMessage", "beta")
patch_operation_explicit_version(IBugNomination, "approve", "beta")
patch_operation_explicit_version(IBugNomination, "canApprove", "beta")
patch_operation_explicit_version(IBugNomination, "decline", "beta")
patch_operation_explicit_version(IBug, "setCommentVisibility", "beta")
patch_operation_explicit_version(IBug, "setPrivate", "beta")
patch_operation_explicit_version(IBug, "setSecurityRelated", "beta")
patch_operation_explicit_version(IBug, "subscribe", "beta")
patch_operation_explicit_version(IBugSubscription, "canBeUnsubscribedByUser", "beta")
patch_operation_explicit_version(IBugSubscriptionFilter, "delete", "beta")
patch_operation_explicit_version(IBugTask, "findSimilarBugs", "beta")
patch_operation_explicit_version(IBugTask, "transitionToAssignee", "beta")
patch_operation_explicit_version(IBugTask, "transitionToImportance", "beta")
patch_operation_explicit_version(IBugTask, "transitionToMilestone", "beta")
patch_operation_explicit_version(IBugTask, "transitionToStatus", "beta")
patch_operation_explicit_version(IBugTask, "transitionToTarget", "beta")
patch_operation_explicit_version(IBugTracker, "addRemoteComponentGroup", "beta")
patch_operation_explicit_version(IBugTrackerComponentGroup, "addComponent", "beta")
patch_operation_explicit_version(IBugTracker, "getAllRemoteComponentGroups", "beta")
patch_operation_explicit_version(IBugTracker, "getRemoteComponentGroup", "beta")
patch_operation_explicit_version(IBugTrackerSet, "ensureBugTracker", "beta")
patch_operation_explicit_version(IBugTrackerSet, "getByName", "beta")
patch_operation_explicit_version(IBugTrackerSet, "queryByBaseURL", "beta")
patch_operation_explicit_version(IBug, "unlinkBranch", "beta")
patch_operation_explicit_version(IBug, "unlinkCVE", "beta")
patch_operation_explicit_version(IBug, "unlinkHWSubmission", "beta")
patch_operation_explicit_version(IBug, "unsubscribe", "beta")
patch_operation_explicit_version(IBug, "unsubscribeFromDupes", "beta")
patch_operation_explicit_version(IBuilderSet, "getByName", "beta")
patch_operation_explicit_version(ICodeImport, "requestImport", "beta")
patch_operation_explicit_version(ICodeReviewVoteReference, "claimReview", "beta")
patch_operation_explicit_version(ICodeReviewVoteReference, "delete", "beta")
patch_operation_explicit_version(ICodeReviewVoteReference, "reassignReview", "beta")
patch_operation_explicit_version(ICountrySet, "getByCode", "beta")
patch_operation_explicit_version(ICountrySet, "getByName", "beta")
patch_operation_explicit_version(IDistribution, "addOfficialBugTag", "beta")
patch_operation_explicit_version(IDistribution, "getArchive", "beta")
patch_operation_explicit_version(IDistribution, "getCommercialPPAs", "beta")
patch_operation_explicit_version(IDistribution, "getCountryMirror", "beta")
patch_operation_explicit_version(IDistribution, "getDevelopmentSeries", "beta")
patch_operation_explicit_version(IDistribution, "getMilestone", "beta")
patch_operation_explicit_version(IDistribution, "getMirrorByName", "beta")
patch_operation_explicit_version(IDistribution, "getSeries", "beta")
patch_operation_explicit_version(IDistribution, "getSourcePackage", "beta")
patch_operation_explicit_version(IDistribution, "getTranslationImportQueueEntries", "beta")
patch_operation_explicit_version(IDistributionMirror, "canTransitionToCountryMirror", "beta")
patch_operation_explicit_version(IDistributionMirror, "getOverallFreshness", "beta")
patch_operation_explicit_version(IDistributionMirror, "isOfficial", "beta")
patch_operation_explicit_version(IDistributionMirror, "transitionToCountryMirror", "beta")
patch_operation_explicit_version(IDistribution, "removeOfficialBugTag", "beta")
patch_operation_explicit_version(IDistribution, "searchSourcePackages", "beta")
patch_operation_explicit_version(IDistribution, "setBugSupervisor", "beta")
patch_operation_explicit_version(IDistributionSourcePackage, "bugtasks", "beta")
patch_operation_explicit_version(IDistributionSourcePackage, "getBranches", "beta")
patch_operation_explicit_version(IDistributionSourcePackage, "getMergeProposals", "beta")
patch_operation_explicit_version(IDistroSeries, "deriveDistroSeries", "beta")
patch_operation_explicit_version(IDistroSeriesDifference, "addComment", "beta")
patch_operation_explicit_version(IDistroSeriesDifference, "blacklist", "beta")
patch_operation_explicit_version(IDistroSeriesDifference, "requestPackageDiffs", "beta")
patch_operation_explicit_version(IDistroSeriesDifference, "unblacklist", "beta")
patch_operation_explicit_version(IDistroSeries, "getDerivedSeries", "beta")
patch_operation_explicit_version(IDistroSeries, "getDistroArchSeries", "beta")
patch_operation_explicit_version(IDistroSeries, "getPackageUploads", "beta")
patch_operation_explicit_version(IDistroSeries, "getSourcePackage", "beta")
patch_operation_explicit_version(IDistroSeries, "getTranslationImportQueueEntries", "beta")
patch_operation_explicit_version(IDistroSeries, "getTranslationTemplates", "beta")
patch_operation_explicit_version(IDistroSeries, "newMilestone", "beta")
patch_operation_explicit_version(IHasTranslationImports, "getTranslationImportQueueEntries", "beta")
patch_operation_explicit_version(IHWDBApplication, "deviceDriverOwnersAffectedByBugs", "beta")
patch_operation_explicit_version(IHWDBApplication, "devices", "beta")
patch_operation_explicit_version(IHWDBApplication, "drivers", "beta")
patch_operation_explicit_version(IHWDBApplication, "hwInfoByBugRelatedUsers", "beta")
patch_operation_explicit_version(IHWDBApplication, "numDevicesInSubmissions", "beta")
patch_operation_explicit_version(IHWDBApplication, "numOwnersOfDevice", "beta")
patch_operation_explicit_version(IHWDBApplication, "numSubmissionsWithDevice", "beta")
patch_operation_explicit_version(IHWDBApplication, "vendorIDs", "beta")
patch_operation_explicit_version(IHWDeviceClass, "delete", "beta")
patch_operation_explicit_version(IHWDevice, "getOrCreateDeviceClass", "beta")
patch_operation_explicit_version(IHWDevice, "getSubmissions", "beta")
patch_operation_explicit_version(IHWDevice, "removeDeviceClass", "beta")
patch_operation_explicit_version(IHWDriver, "getSubmissions", "beta")
patch_operation_explicit_version(ILanguageSet, "getAllLanguages", "beta")
patch_operation_explicit_version(IMaloneApplication, "createBug", "beta")
patch_operation_explicit_version(IMilestone, "createProductRelease", "beta")
patch_operation_explicit_version(IMilestone, "destroySelf", "beta")
patch_operation_explicit_version(IPackageset, "addSources", "beta")
patch_operation_explicit_version(IPackageset, "addSubsets", "beta")
patch_operation_explicit_version(IPackageset, "getSourcesIncluded", "beta")
patch_operation_explicit_version(IPackageset, "getSourcesNotSharedBy", "beta")
patch_operation_explicit_version(IPackageset, "getSourcesSharedBy", "beta")
patch_operation_explicit_version(IPackageset, "relatedSets", "beta")
patch_operation_explicit_version(IPackageset, "removeSources", "beta")
patch_operation_explicit_version(IPackageset, "removeSubsets", "beta")
patch_operation_explicit_version(IPackagesetSet, "getByName", "beta")
patch_operation_explicit_version(IPackagesetSet, "new", "beta")
patch_operation_explicit_version(IPackagesetSet, "setsIncludingSource", "beta")
patch_operation_explicit_version(IPackageset, "setsIncluded", "beta")
patch_operation_explicit_version(IPackageset, "setsIncludedBy", "beta")
patch_operation_explicit_version(IPersonSet, "find", "beta")
patch_operation_explicit_version(IPersonSet, "findPerson", "beta")
patch_operation_explicit_version(IPersonSet, "findTeam", "beta")
patch_operation_explicit_version(IPersonSet, "getByEmail", "beta")
patch_operation_explicit_version(IPersonSet, "newTeam", "beta")
patch_operation_explicit_version(IPillarNameSet, "search", "beta")
patch_operation_explicit_version(IProduct, "addOfficialBugTag", "beta")
patch_operation_explicit_version(IProduct, "getBranches", "beta")
patch_operation_explicit_version(IProduct, "getMergeProposals", "beta")
patch_operation_explicit_version(IProduct, "getMilestone", "beta")
patch_operation_explicit_version(IProduct, "getRelease", "beta")
patch_operation_explicit_version(IProduct, "getSeries", "beta")
patch_operation_explicit_version(IProduct, "getTimeline", "beta")
patch_operation_explicit_version(IProduct, "getTranslationImportQueueEntries", "beta")
patch_operation_explicit_version(IProduct, "newCodeImport", "beta")
patch_operation_explicit_version(IProduct, "newSeries", "beta")
patch_operation_explicit_version(IProductRelease, "addReleaseFile", "beta")
patch_operation_explicit_version(IProductRelease, "destroySelf", "beta")
patch_operation_explicit_version(IProductReleaseFile, "destroySelf", "beta")
patch_operation_explicit_version(IProduct, "removeOfficialBugTag", "beta")
patch_operation_explicit_version(IProductSeries, "getTimeline", "beta")
patch_operation_explicit_version(IProductSeries, "getTranslationImportQueueEntries", "beta")
patch_operation_explicit_version(IProductSeries, "getTranslationTemplates", "beta")
patch_operation_explicit_version(IProductSeries, "newMilestone", "beta")
patch_operation_explicit_version(IProduct, "setBugSupervisor", "beta")
patch_operation_explicit_version(IProductSet, "createProduct", "beta")
patch_operation_explicit_version(IProductSet, "forReview", "beta")
patch_operation_explicit_version(IProductSet, "latest", "beta")
patch_operation_explicit_version(IProductSet, "search", "beta")
patch_operation_explicit_version(IProjectGroup, "getBranches", "beta")
patch_operation_explicit_version(IProjectGroup, "getMergeProposals", "beta")
patch_operation_explicit_version(IProjectGroup, "getMilestone", "beta")
patch_operation_explicit_version(IProjectGroupSet, "search", "beta")
patch_operation_explicit_version(ISourcePackage, "getBranch", "beta")
patch_operation_explicit_version(ISourcePackage, "getBranches", "beta")
patch_operation_explicit_version(ISourcePackage, "getMergeProposals", "beta")
patch_operation_explicit_version(ISourcePackage, "getTranslationImportQueueEntries", "beta")
patch_operation_explicit_version(ISourcePackage, "getTranslationTemplates", "beta")
patch_operation_explicit_version(ISourcePackage, "linkedBranches", "beta")
patch_operation_explicit_version(ISourcePackage, "newCodeImport", "beta")
patch_operation_explicit_version(ISourcePackagePublishingHistory, "api_requestDeletion", "beta")
patch_operation_explicit_version(ISourcePackagePublishingHistory, "binaryFileUrls", "beta")
patch_operation_explicit_version(ISourcePackagePublishingHistory, "changesFileUrl", "beta")
patch_operation_explicit_version(ISourcePackagePublishingHistory, "getBuilds", "beta")
patch_operation_explicit_version(ISourcePackagePublishingHistory, "getPublishedBinaries", "beta")
patch_operation_explicit_version(ISourcePackagePublishingHistory, "packageDiffUrl", "beta")
patch_operation_explicit_version(ISourcePackagePublishingHistory, "sourceFileUrls", "beta")
patch_operation_explicit_version(ISourcePackageRecipe, "performDailyBuild", "beta")
patch_operation_explicit_version(ISourcePackageRecipe, "requestBuild", "beta")
patch_operation_explicit_version(ISourcePackageRecipe, "setRecipeText", "beta")
patch_operation_explicit_version(ISourcePackage, "setBranch", "beta")
patch_operation_explicit_version(ISpecification, "linkBranch", "beta")
patch_operation_explicit_version(ISpecification, "unlinkBranch", "beta")
patch_operation_explicit_version(IStructuralSubscription, "delete", "beta")
patch_operation_explicit_version(IStructuralSubscription, "newBugFilter", "beta")
patch_operation_explicit_version(ITeamMembership, "setExpirationDate", "beta")
patch_operation_explicit_version(ITeamMembership, "setStatus", "beta")
patch_operation_explicit_version(ITemporaryBlobStorage, "getProcessedData", "beta")
patch_operation_explicit_version(ITemporaryBlobStorage, "hasBeenProcessed", "beta")
patch_operation_explicit_version(ITemporaryStorageManager, "fetch", "beta")
patch_operation_explicit_version(ITranslationImportQueueEntry, "setStatus", "beta")
patch_operation_explicit_version(ITranslationImportQueue, "getAllEntries", "beta")
patch_operation_explicit_version(ITranslationImportQueue, "getFirstEntryToImport", "beta")
patch_operation_explicit_version(ITranslationImportQueue, "getRequestTargets", "beta")
