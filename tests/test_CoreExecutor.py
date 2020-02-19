import os
import tempfile
import unittest

from cwlkernel.CoreExecutor import CoreExecutor
from cwlkernel.IOManager import IOFileManager


class CoreExecutorTests(unittest.TestCase):
    data_directory: str
    cwl_directory: str
    kernel_root_directory: str
    maxDiff = None

    @classmethod
    def setUpClass(cls) -> None:
        cls.data_directory = os.sep.join([os.path.dirname(os.path.realpath(__file__)), 'input_data'])
        cls.cwl_directory = os.sep.join([os.path.dirname(os.path.realpath(__file__)), 'cwl'])
        cls.kernel_root_directory = tempfile.mkdtemp()

    def test_execute(self):
        # That tests fails only when is called through PyCharm
        file_manager = IOFileManager(self.kernel_root_directory)
        executor = CoreExecutor(file_manager)
        with open(os.sep.join([self.cwl_directory, 'essential_input.cwl'])) as f:
            workflow_str = f.read()
        executor.set_workflow(workflow_str)
        with open(os.sep.join([self.data_directory, 'essential_input_data1.yml'])) as f:
            data_str = f.read()
        executor.set_data([data_str])
        try:
            executor.execute()
        except Exception:
            self.fail("execution failed")


if __name__ == '__main__':
    unittest.main()
