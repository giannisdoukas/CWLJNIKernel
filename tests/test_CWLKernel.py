import unittest
from cwlkernel.CWLKernel import CWLKernel
from ruamel import yaml
import os

class CWLKernelTests(unittest.TestCase):

    data_directory: str
    maxDiff = None

    @classmethod
    def setUpClass(cls) -> None:
        cls.data_directory = os.sep.join([os.path.dirname(os.path.realpath(__file__)), 'input_data'])

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

if __name__ == '__main__':
    unittest.main()
