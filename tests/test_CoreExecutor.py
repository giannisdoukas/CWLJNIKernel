import os
import tempfile
import unittest
from pathlib import Path

from cwlkernel.CoreExecutor import CoreExecutor
from cwlkernel.IOManager import IOFileManager


class TestCoreExecutor(unittest.TestCase):
    data_directory: str
    cwl_directory: str
    kernel_root_directory: str
    maxDiff = None

    @classmethod
    def setUpClass(cls) -> None:
        cls.data_directory = os.sep.join([os.path.dirname(os.path.realpath(__file__)), 'input_data'])
        cls.cwl_directory = os.sep.join([os.path.dirname(os.path.realpath(__file__)), 'cwl'])
        cls.kernel_root_directory = tempfile.mkdtemp()

    def test_executor_execute(self):
        # That tests fails only when is called through PyCharm
        file_manager = IOFileManager(self.kernel_root_directory)
        executor = CoreExecutor(file_manager, None)
        workflow_path = os.sep.join([self.cwl_directory, 'essential_input.cwl'])
        executor.set_workflow_path(workflow_path)
        with open(os.sep.join([self.data_directory, 'essential_input_data1.yml'])) as f:
            data_str = f.read()
        executor.set_data([data_str])
        try:
            execution_id, new_files, exception, research_object = executor.execute()
            self.assertIsNotNone(execution_id)
            self.assertDictEqual(new_files, {})
            self.assertIsNone(exception, 'An exception occurred while executing workflow')
            self.assertIsNone(research_object, 'Research object must be none when provenance is disabled')
        except Exception:
            self.fail("execution failed")

    def test_validate_input_files(self):
        import uuid
        absolute_file_does_exists = {
            'example_flag': True,
            'example_string': 'hello',
            'example_int': 42,
            'example_file': {
                'class': 'File',
                'location': f'/NOT_EXISTING_FILENAME-{uuid.uuid4()}.txt'
            }
        }
        self.assertRaises(
            FileNotFoundError, CoreExecutor.validate_input_files, absolute_file_does_exists, Path(self.data_directory)
        )
        relative_file_does_exists = {
            'example_flag': True,
            'example_string': 'hello',
            'example_int': 42,
            'example_file': {
                'class': 'File',
                'location': f'NOT_EXISTING_FILENAME-{uuid.uuid4()}.txt'
            }
        }
        self.assertRaises(
            FileNotFoundError, CoreExecutor.validate_input_files, relative_file_does_exists, Path(self.data_directory)
        )


if __name__ == '__main__':
    unittest.main()
