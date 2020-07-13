import os
import shutil
import tempfile
import unittest
from os.path import sep

from cwlkernel.IOManager import IOFileManager


class TestIOManager(unittest.TestCase):
    root_directory: str

    def setUp(self) -> None:
        self.root_directory = tempfile.mkdtemp()

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

    def test_append_files(self):
        source_tmp_dir = tempfile.mkdtemp()
        files = [os.path.join(source_tmp_dir, 'tmpfilefortest')]
        with open(files[0], 'w') as f:
            f.write('tmp text')
        file_manager = IOFileManager(self.root_directory)
        new_files = file_manager.append_files(files)

        self.assertListEqual(
            [os.path.basename(f) for f in new_files],
            [os.path.basename(f) for f in os.listdir(self.root_directory) if
             os.path.isfile(os.path.join(self.root_directory, f))]
        )
        with open(new_files[0]) as f:
            copy_text = f.read()
        self.assertEqual(copy_text, 'tmp text')

    def tearDown(self) -> None:
        try:
            shutil.rmtree(self.root_directory)
        except:
            pass


if __name__ == '__main__':
    unittest.main()
