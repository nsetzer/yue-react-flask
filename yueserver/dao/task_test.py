import os
import unittest
import json
import time
import random

from .task import TaskQueue, \
    TaskExecutionException, TaskTimeoutException, TaskAlreadyJoinedException

def return_input(*args, **kwargs):
    if kwargs.get('throw', False):
        raise Exception("Task Error")
    if 'sleep' in kwargs:
        time.sleep(kwargs['sleep'])
    return args, kwargs

class TaskQueueTestCase(unittest.TestCase):

    def test_queue_0(self):
        # test with no threads
        queue = TaskQueue(0)
        job_id = queue.submit(return_input, 0)
        result = queue.wait(job_id)
        queue.stop()
        self.assertEqual(result[0][0], 0)

    def test_queue_1(self):
        # test with 1 thread

        queue = TaskQueue(1)
        job_id = queue.submit(return_input, 0)
        result = queue.wait(job_id)
        queue.stop()
        self.assertEqual(result[0][0], 0)

    def test_queue_2(self):
        # test with 2 thread

        queue = TaskQueue(2)
        job_id1 = queue.submit(return_input, 1)
        job_id2 = queue.submit(return_input, 2)
        job_id3 = queue.submit(return_input, 3)
        result1 = queue.wait(job_id1)
        result2 = queue.wait(job_id2)
        result3 = queue.wait(job_id3)
        queue.stop()
        self.assertEqual(result1[0][0], 1)
        self.assertEqual(result2[0][0], 2)
        self.assertEqual(result3[0][0], 3)

    def test_queue_error(self):
        # test with 1 thread

        queue = TaskQueue(1)
        job_id = queue.submit(return_input, 0, throw=True)

        with self.assertRaises(TaskExecutionException):
            result = queue.wait(job_id)

        queue.stop()

    def test_queue_timeout(self):
        # test with 1 thread

        queue = TaskQueue(1)
        job_id = queue.submit(return_input, 0, sleep=.1)

        with self.assertRaises(TaskTimeoutException):
            result = queue.wait(job_id, .05)

        # this unfortunately means we have to wait for
        # the sleeping thread to finish
        queue.stop()

    def test_queue_join_twice(self):
        # test with 1 thread

        queue = TaskQueue(1)
        job_id = queue.submit(return_input, 0)

        result = queue.wait(job_id)
        with self.assertRaises(TaskAlreadyJoinedException):
            result = queue.wait(job_id)

        queue.stop()

    def test_queue_autodelete(self):

        # expire results
        queue = TaskQueue(1, .05)
        job_id = queue.submit(return_input, 0)

        time.sleep(.1)

        _ = queue.submit(return_input, 0)

        # job was deleted on submit, due to expiry settings
        with self.assertRaises(TaskAlreadyJoinedException):
            result = queue.wait(job_id)

        queue.stop()

def main():
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(TaskQueueTestCase)
    unittest.TextTestRunner().run(suite)

if __name__ == '__main__':
    main()
