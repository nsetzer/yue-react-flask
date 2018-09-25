
import sys
import unittest
import json
import io
from threading import Thread
import time

from ..db import main_test

from .util import BytesFIFO, BytesFIFOWriter, BytesFIFOReader
from .filesys import FileSystem, sh_escape
from .s3fs import S3FileSystemImpl

class TestReaderThread(Thread):
    def __init__(self, fifo, chunk_size):
        super(TestReaderThread, self).__init__()
        self.fifo = fifo
        self.chunk_size = chunk_size
        self.count = 0

    def run(self):
        reader = BytesFIFOReader(self.fifo)
        try:
            buf = reader.read(self.chunk_size)
            while buf:
                self.count += len(buf)
                buf = reader.read(self.chunk_size)
        finally:
            reader.close()

class TestWriterThread(Thread):
    def __init__(self, fifo, chunk_size, iterations, delay=0.0):
        super(TestWriterThread, self).__init__()
        self.fifo = fifo
        self.chunk_size = chunk_size
        self.iterations = iterations
        self.delay = delay
        self.count = 0

    def run(self):
        writer = BytesFIFOWriter(self.fifo)
        try:
            for i in range(self.iterations):
                writer.write(b"0" * self.chunk_size)
                self.count += self.chunk_size
                if self.delay > 0.0:
                    time.sleep(self.delay)
        finally:
            writer.close()

class BytesFifoTestCase(unittest.TestCase):

    def test_rw_a(self):

        # simple test, read and write the same amount of data
        fifo = BytesFIFO()
        reader = TestReaderThread(fifo, 1024)
        writer = TestWriterThread(fifo, 1024, 10)
        reader.start()
        writer.start()
        reader.join()
        writer.join()

        self.assertEqual(reader.count, writer.count)

    def test_rw_b(self):
        # force a resize when writing
        # a resize is a write, which calls resize, which calls read
        # potential for deadlock when not implemented correctly
        fifo = BytesFIFO()
        reader = TestReaderThread(fifo, 256)
        writer = TestWriterThread(fifo, 4096, 10)
        reader.start()
        writer.start()
        reader.join()
        writer.join()

        self.assertEqual(reader.count, writer.count)

    def test_rw_c(self):
        # read all data
        fifo = BytesFIFO()
        reader = TestReaderThread(fifo, -1)
        writer = TestWriterThread(fifo, 1024, 10)
        reader.start()
        writer.start()
        reader.join()
        writer.join()

        self.assertEqual(reader.count, writer.count)

    def test_rw_d(self):
        # read all data
        fifo = BytesFIFO(max_size=1024)
        reader = TestReaderThread(fifo, 1024)
        writer = TestWriterThread(fifo, 2048, 10)
        reader.start()
        writer.start()
        reader.join()
        writer.join()

        self.assertEqual(reader.count, writer.count)

if __name__ == '__main__':
    main_test(sys.argv, globals())

