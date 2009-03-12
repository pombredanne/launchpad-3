# Copyright 2007-2009 Canonical Ltd.  All rights reserved.

__metaclass__ = type

__all__ = ['LoopTuner']


import logging
import time

from canonical.launchpad.interfaces.looptuner import ITunableLoop


class LoopTuner:
    """A loop that tunes itself to approximate an ideal time per iteration.

    Use this for large processing jobs that need to be broken down into chunks
    of such size that processing a single chunk takes approximately a given
    ideal time.  For example, large database operations may have to be
    performed and committed in a large number of small steps in order to avoid
    locking out other clients that need to access the same data.  Regular
    commits allow other clients to get their work done.

    In such a situation, committing for every step is often far too costly.
    Imagine inserting a million rows and committing after every row!  You
    could hand-pick a static number of steps per commit, but that takes a lot
    of experimental guesswork and it will still waste time when things go
    well, and on the other hand, it will still end up taking too much time per
    batch when the system slows down for whatever reason.

    Instead, define your loop body in an ITunableLoop; parameterize it on the
    number of steps per batch; say how much time you'd like to spend per
    batch; and pass it to a LoopTuner.  The LoopTuner will execute your loop,
    dynamically tuning its batch-size parameter to stay close to your time
    goal.  If things go faster than expected, it will ask your loop body to do
    more work for the next batch.  If a batch takes too much time, the next
    batch will be smaller.  There is also some cushioning for one-off spikes
    and troughs in processing speed.
    """

    def __init__(self, operation, goal_seconds, minimum_chunk_size=1,
            maximum_chunk_size=1000000000, cooldown_time=None):
        """Initialize a loop, to be run to completion at most once.

        Parameters:

        operation: an object implementing the loop body.  It must support the
            ITunableLoop interface.

        goal_seconds: the ideal number of seconds for any one iteration to
            take.  The algorithm will vary chunk size in order to stick close
            to this ideal.

        minimum_chunk_size: the smallest chunk size that is reasonable.  The
            tuning algorithm will never let chunk size sink below this value.

        maximum_chunk_size: the largest allowable chunk size.  A maximum is
            needed even if the ITunableLoop ignores chunk size for whatever
            reason, since reaching floating-point infinity would seriously
            break the algorithm's arithmetic.
        cooldown_time: time (in seconds, float) to sleep between consecutive
            operation runs.  Defaults to None for no sleep.
        """
        assert(ITunableLoop.providedBy(operation))
        self.operation = operation
        self.goal_seconds = float(goal_seconds)
        self.minimum_chunk_size = minimum_chunk_size
        self.maximum_chunk_size = maximum_chunk_size
        self.cooldown_time = cooldown_time

    def run(self):
        """Run the loop to completion."""
        chunk_size = self.minimum_chunk_size
        iteration = 0
        total_size = 0
        start_time = self._time()
        last_clock = start_time
        while not self.operation.isDone():
            self.operation(chunk_size)

            new_clock = self._time()
            time_taken = new_clock - last_clock
            last_clock = new_clock
            logging.info("Iteration %d (size %.1f): %.3f seconds" %
                         (iteration, chunk_size, time_taken))

            last_clock = self._coolDown(last_clock)

            total_size += chunk_size

            # Adjust parameter value to approximate goal_seconds.  The new
            # value is the average of two numbers: the previous value, and an
            # estimate of how many rows would take us to exactly goal_seconds
            # seconds.
            # The weight in this estimate of any given historic measurement
            # decays exponentially with an exponent of 1/2.  This softens the
            # blows from spikes and dips in processing time.
            # Set a reasonable minimum for time_taken, just in case we get
            # weird values for whatever reason and destabilize the
            # algorithm.
            time_taken = max(self.goal_seconds/10, time_taken)
            chunk_size *= (1 + self.goal_seconds/time_taken)/2
            chunk_size = max(chunk_size, self.minimum_chunk_size)
            chunk_size = min(chunk_size, self.maximum_chunk_size)
            iteration += 1

        total_time = last_clock - start_time
        average_size = total_size/max(1, iteration)
        average_speed = total_size/max(1, total_time)
        logging.info(
            "Done. %d items in %d iterations, "
            "%.3f seconds, "
            "average size %f (%s/s)" %
                (total_size, iteration, total_time, average_size,
                 average_speed))

    def _coolDown(self, bedtime):
        """Sleep for `self.cooldown_time` seconds, if set.

        Assumes that anything the main LoopTuner loop does apart from
        doing a chunk of work or sleeping takes zero time.

        :param bedtime: Time the cooldown started, i.e. the time the
        chunk of real work was completed.
        :return: Time when cooldown completed, i.e. the starting time
        for a next chunk of work.
        """
        if self.cooldown_time is None or self.cooldown_time <= 0.0:
            return bedtime
        else:
            time.sleep(self.cooldown_time)
            return self._time()

    def _time(self):
        """Monotonic system timer with unit of 1 second.

        Overridable so tests can fake processing speeds accurately and without
        actually waiting.
        """
        return time.time()

