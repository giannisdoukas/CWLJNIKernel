import os
import shutil
import tempfile
import unittest
from os.path import sep

from cwlkernel.IOManager import IOFileManager


class TestIOManager(unittest.TestCase):
    root_directory: str

    @classmethod
    def setUpClass(cls) -> None:
        cls.root_directory = tempfile.mkdtemp()


    def test_read(self):
        fd, filename = tempfile.mkstemp(prefix='CWLJNKernelUnittests_', dir=self.root_directory)
        test_text = b'test text'
        with open(fd, 'wb') as f:
            f.write(test_text)

        tmp_filename = filename.split(sep)[-1]
        iofile_manager = IOFileManager(self.root_directory)
        text = iofile_manager.read(tmp_filename)
        self.assertEqual(test_text, text)
        os.remove(filename)

    def test_write(self):
        text_to_write = b'text to write'
        fd, filename = tempfile.mkstemp(prefix='CWLJNKernelUnittests_', dir=self.root_directory)
        file_manager = IOFileManager(self.root_directory)
        tmp_filename = filename.split(sep)[-1]
        file_manager.write(tmp_filename, text_to_write)

        with open(filename, 'rb') as f:
            text = f.read()
        self.assertEqual(text_to_write, text)


    @classmethod
    def tearDownClass(cls) -> None:
        shutil.rmtree(cls.root_directory)


if __name__ == '__main__':
    unittest.main()
