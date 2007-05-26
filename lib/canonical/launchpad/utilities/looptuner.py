import logging
import time

class TunedLoop:
    """Base class for self-tuning loop bodies to be driven by LoopTuner.

    To construct a self-tuning batched loop, define your loop body as a
    derivative of TunedLoop and pass an instance to your LoopTuner.
    """
    def done(self):
        """Is this loop finished?

        Once this returns True, the LoopTuner will no longer touch this
        object.
        """
        return True

    def perform(self, chunk_size):
        """Perform an iteration of the loop.

        The chunk_size parameter says (in some way you define) how much work
        the LoopTuner believes you should try to do in this iteration in order
        to get as close as possible to your time goal.
        """
        pass

    def post(self, chunk_size):
        """Perform any work at the end of an iteration that should not be
        counted towards the iteration's time budget.
        """
        pass


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

    Instead, define your loop body in a subclass of TunedLoop; parameterize it
    on the number of steps per batch; say how much time you'd like to spend
    per batch; and pass it to a LoopTuner.  The LoopTuner will execute your
    loop, dynamically tuning its batch-size parameter to stay close to your
    time goal.  If things go faster than expected, it will ask your loop body
    to do more work for the next batch.  If a batch takes too much time, the
    next batch will be smaller.  There is also some cushioning for one-off
    spikes and troughs in processing speed.
    """

    def __init__(self, operation, time_goal, minimum_chunk_size):
        """Initialize a loop, to be run to completion at most once.

        Parameters:

        operation: an object implementing the loop body.  It should support at
        least the interface of the TunedLoop class.

        time_goal: the ideal number of seconds for any one iteration to take.
            The algorithm will vary chunk size in order to stick close to this
            ideal.

        minimum_chunk_size: the smallest chunk size that is reasonable.  The
            tuning algorithm will never let chunk size sink below this value.
        """

        self.operation = operation
        self.time_goal = time_goal
        self.minimum_chunk_size = minimum_chunk_size


    def run(self):
        """Run the loop to completion."""
        chunk_size = self.minimum_chunk_size
        iteration = 0
        total_size = 0
        time_taken = self.time_goal
        start_time = time.time()
        while not self.operation.done():
            iteration_start_time = time.time()

            self.operation.perform(chunk_size)

            time_taken = time.time() - iteration_start_time
            logging.info("Iteration %d (%d): %.3f seconds" % (
                            iteration, chunk_size, time_taken))

            self.operation.post(chunk_size)

            total_size += chunk_size

            # Adjust parameter value to approximate time_goal.  The new
            # value is the average of two numbers: the previous value, and an
            # estimate of how many rows would take us to exactly time_goal
            # seconds.
            # The weight in this estimate of any given historic measurement
            # decays exponentially with an exponent of 1/2.  This softens the
            # blows from spikes and dips in processing time.
            # Set a reasonable minimum for time_taken, just in case we get
            # weird values for whatever reason and destabilize the
            # algorithm.
            time_taken = max(self.time_goal/10, time_taken)
            chunk_size *= (1 + self.time_goal/time_taken)/2
            chunk_size = max(chunk_size, self.minimum_chunk_size)
            iteration += 1

        total_time = time.time() - start_time
        average_size = total_size/iteration
        average_speed = total_size/total_time
        logging.info(
            "Done. %d items in %d iterations, "
            "%.3f seconds, "
            "average size %f (%s/s)" % 
                (total_size, iteration, total_time, average_size,
                 average_speed))

