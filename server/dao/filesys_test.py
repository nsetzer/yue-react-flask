
import unittest
import json


from .filesys import FileSystem


class FileSystemTestCase(unittest.TestCase):

    def test_memfs(self):

        fs = FileSystem()

        path = "mem:///test/file.txt"
        msg = b"hello world\n"

        self.assertFalse(fs.exists(path))

        with fs.open(path, "wb") as wb:
            wb.write(msg)

        self.assertTrue(fs.exists(path))

        with fs.open(path, "rb") as rb:
            self.assertEqual(msg, rb.read())

        scheme, parts = fs.parts(path)
        parent = scheme + fs.join(*parts[:-1])
        items = fs.listdir(parent)
        self.assertEqual(len(items), 1)
        self.assertTrue(fs.samefile(fs.join(parent, items[0]), path))

        self.assertTrue(fs.isfile(path))
        self.assertFalse(fs.isfile(parent))

        self.assertFalse(fs.isdir(path))
        self.assertTrue(fs.isdir(parent))

        for name, is_dir, size, mtime in fs.scandir(parent):
            self.assertEqual(size, len(msg))

def main():
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(FileSystemTestCase)
    unittest.TextTestRunner().run(suite)

if __name__ == '__main__':
    main()