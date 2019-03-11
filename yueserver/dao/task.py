
# TODO: unit tests
#       clean up old result sets after 60? seconds
import time
import logging
from threading import Thread, Lock, Condition
import uuid
import atexit

class TaskException(Exception):
    pass

class TaskExecutionException(TaskException):

    def __init__(self, e=None):
        super(TaskExecutionException, self).__init__(str(e))
        self.original = e

class TaskTimeoutException(Exception):

    def __init__(self, msg):
        super(TaskTimeoutException, self).__init__(msg)

class TaskAlreadyJoinedException(Exception):

    def __init__(self, msg):
        super(TaskAlreadyJoinedException, self).__init__(msg)

class _Task(Thread):
    def __init__(self, parent):
        super(_Task, self).__init__()
        self.parent = parent
        self.cv = parent.cv_tasks

        self._alive = True

        # indicate that this thread should not block the process from exiting
        self.daemon = True

    def run(self):

        while self._alive:

            tid = None
            op = None

            with self.cv:

                # wait for a task to be available
                while len(self.parent._queue) == 0 and self._alive:
                    self.cv.wait()

                # get a task to execute
                if len(self.parent._queue) > 0:
                    tid = self.parent._queue.pop()  # TODO FIFO?
                    op = self.parent._tasks[tid]

            if op is not None:
                retval = self.execute(*op)

                # delete the task
                with self.cv:
                    del self.parent._tasks[tid]
                    self.parent._results[tid] = retval
                    self.cv.notify_all()

    def execute(self, fn, args, kwargs):
        """
        returns a tuple (return_value, exception)
        """

        try:
            return fn(*args, **kwargs), None, time.time()
        except Exception as e:
            return None, e, time.time()

class TaskQueue(object):
    """
    Execute functions in a separate thread

    tasks are callable objects, tasks can be joined using
    the task id returned when the task is submitted.
    joining a task re-raises an exception if one was thrown
    or returns the original return value of the function

    """
    def __init__(self, size=2, expire=60):
        """
        size: the number of threads to start
        expire: auto delete task results older than N seconds
                set to -1 to disable auto delete
        """
        super(TaskQueue, self).__init__()

        self.expire = expire
        # the order the tasks were submitted
        self._queue = []
        self._tasks = {}
        self._results = {}

        self._threads = []

        self.lk_tasks = Lock()
        self.cv_tasks = Condition(self.lk_tasks)

        for i in range(size):
            t = _Task(self)

            t.start()
            self._threads.append(t)

        # when the main thread exits, if this queue is still running
        # join threads
        atexit.register(self._atexit_stop)

    def submit(self, fn, *args, **kwargs):

        tid = str(uuid.uuid4())

        if len(self._threads) == 0:
            self._execute(tid, fn, args, kwargs)
            return tid

        with self.cv_tasks:

            e = time.time()
            for _tid in list(self._results.keys()):
                _, _, t = self._results[_tid]
                if self.expire >= 0 and (e - t) > self.expire:
                    del self._results[_tid]

            self._tasks[tid] = (fn, args, kwargs)
            self._queue.append(tid)
            self.cv_tasks.notify_all()

        return tid

    def _execute(self, tid, fn, args, kwargs):
        """task executor for un-threaded processing"""
        with self.cv_tasks:
            try:
                self._results[tid] = (fn(*args, **kwargs), None, time.time())
            except Exception as e:
                self._results[tid] = (None, e, time.time())

    def wait(self, tid, timeout=None):
        """
        timeout: float: seconds

        raises TaskException:
            TaskTimeoutException: timeout expired
            TaskExecutionException: re-raise a task exception
        """

        s = time.time()
        retval = None
        with self.cv_tasks:

            while tid in self._tasks:
                d = None
                if timeout is not None:
                    elapsed = time.time() - s
                    d = timeout - elapsed
                    if d < 0:
                        raise TaskTimeoutException("timer expired")
                self.cv_tasks.wait(d)

            if tid not in self._results:
                raise TaskAlreadyJoinedException(tid)

            retval = self._results[tid]
            del self._results[tid]

        r, e, t = retval
        if e is not None:
            raise TaskExecutionException(e).with_traceback(e.__traceback__)
        return r

    def stop(self):

        with self.cv_tasks:
            logging.info("TaskQueue joining %d threads", len(self._threads))

            for t in self._threads:
                t._alive = False
            self.cv_tasks.notify_all()

        for t in self._threads:
            t.join()

        self._threads = []

        atexit.unregister(self._atexit_stop)

    def _atexit_stop(self):
        logging.error("TaskQueue shutting down")
        self.stop()