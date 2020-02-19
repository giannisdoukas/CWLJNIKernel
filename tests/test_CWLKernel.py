import tempfile
import unittest

from cwlkernel.CWLExecuteConfigurator import CWLExecuteConfigurator
from cwlkernel.CWLKernel import CWLKernel
from ruamel import yaml
import os

class CWLKernelTests(unittest.TestCase):
    data_directory: str
    cwl_directory: str
    kernel_root_directory: str
    maxDiff = None

    @classmethod
    def setUpClass(cls) -> None:
        cls.data_directory = os.sep.join([os.path.dirname(os.path.realpath(__file__)), 'input_data'])
        cls.cwl_directory = os.sep.join([os.path.dirname(os.path.realpath(__file__)), 'cwl'])
        cls.kernel_root_directory = tempfile.mkdtemp()

    def test_get_input_data(self):
        kernel = CWLKernel()
        with open(os.sep.join([self.data_directory, 'data1.yml'])) as f:
            data = f.read()
        exec_response = kernel.do_execute(data, False)

        self.assertDictEqual(
            {"status": "ok", "execution_count": 0, 'payload': [], 'user_expressions': {}},
            exec_response
        )
        self.assertListEqual([data], kernel._yaml_input_data)

        exec_response = kernel.do_execute(data, False)
        # The base class increments the execution count. So, exec_count remains 0
        self.assertDictEqual(
            {"status": "ok", "execution_count": 0, 'payload': [], 'user_expressions': {}},
            exec_response
        )
        self.assertListEqual([data, data], kernel._yaml_input_data)


    def test_get_past_results(self):
        kernel = CWLKernel()
        with open(os.sep.join([self.data_directory, 'tar_job.yml'])) as f:
            data = f.read()
        kernel.do_execute(data, False)
        with open(os.sep.join([self.cwl_directory, 'extract_tar.cwl'])) as f:
            workflow_str = f.read()
        kernel.do_execute(workflow_str, False)

        results_dir = kernel._results_manager.ROOT_DIRECTORY
        result_files_in_directory = set([f for f in os.listdir(results_dir) if os.path.isfile(f)])
        return_past_results = set(kernel.get_past_results())
        correct_result = {os.sep.join([results_dir, 'hello.txt'])}
        self.assertSetEqual(correct_result, result_files_in_directory)
        self.assertSetEqual(correct_result, return_past_results)


if __name__ == '__main__':
    unittest.main()
