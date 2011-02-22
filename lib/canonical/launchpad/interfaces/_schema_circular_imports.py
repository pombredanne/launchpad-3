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
    patch_entry_return_type,
    patch_list_parameter_type,
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
from lp.code.interfaces.hasrecipes import IHasRecipes
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
patch_collection_return_type(
    IHasRecipes, 'getRecipes', ISourcePackageRecipe)

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
patch_entry_return_type(
    ISourcePackageRecipe, 'getLastBuild', ISourcePackageRecipeBuild)
patch_collection_return_type(
    ISourcePackageRecipe, 'getPendingBuilds', ISourcePackageRecipeBuild)
patch_collection_return_type(
    ISourcePackageRecipe, 'getCompletedBuilds', ISourcePackageRecipeBuild)
patch_collection_return_type(
    ISourcePackageRecipe, 'getBuilds', ISourcePackageRecipeBuild)

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
patch_collection_property(ISpecification, 'linked_branches', ISpecificationBranch)

# ISpecificationTarget
patch_entry_return_type(
    ISpecificationTarget, 'getSpecification', ISpecification)

# IHasSpecifications
patch_collection_property(
    IHasSpecifications, 'all_specifications', ISpecification)
patch_collection_property(
    IHasSpecifications, 'valid_specifications', ISpecification)
