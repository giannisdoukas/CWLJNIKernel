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
        kernel.do_execute(data, False)

        self.assertListEqual([data], kernel._yaml_input_data)

        kernel.do_execute(data, False)
        self.assertListEqual([data, data], kernel._yaml_input_data)

if __name__ == '__main__':
    unittest.main()
