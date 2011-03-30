from lp.services.job.interfaces.job import (
    IJobSource,
    )


class ITranslationPackagingJobSource(IJobSource):
    """Marker interface for Translation merge jobs."""
