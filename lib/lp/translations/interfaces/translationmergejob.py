from lp.services.job.interfaces.job import (
    IJobSource,
    )


class ITranslationMergeJobSource(IJobSource):
    """Marker interface for Translation merge jobs."""
