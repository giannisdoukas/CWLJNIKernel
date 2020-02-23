import logging
import os
import tarfile
import tempfile
import unittest


class TestCWLKernel(unittest.TestCase):

    data_directory: str
    cwl_directory: str
    kernel_root_directory: str
    maxDiff = None

    @classmethod
    def setUpClass(cls) -> None:
        logging.basicConfig(
            level=logging.DEBUG,
            format='%(asctime)-15s:%(levelname)s:%(name)s:%(process)d:%(message)s'
        )
        cls.data_directory = os.sep.join([os.path.dirname(os.path.realpath(__file__)), 'input_data'])
        cls.cwl_directory = os.sep.join([os.path.dirname(os.path.realpath(__file__)), 'cwl'])
        cls.kernel_root_directory = tempfile.mkdtemp()

    def test_get_input_data(self):
        from cwlkernel.CWLKernel import CWLKernel
        kernel = CWLKernel()
        # cancel send_response
        kernel.send_response = lambda *args, **kwargs: None

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

    def test_execute_echo_cwl(self):
        from cwlkernel.CWLKernel import CWLKernel
        kernel = CWLKernel()
        # cancel send_response
        kernel.send_response = lambda *args, **kwargs: None

        with open(os.sep.join([self.data_directory, 'echo-job.yml'])) as f:
            data = f.read()
        self.assertDictEqual(
            {'status': 'ok', 'execution_count': 0, 'payload': [], 'user_expressions': {}},
            kernel.do_execute(data, False)
        )
        with open(os.sep.join([self.cwl_directory, 'echo.cwl'])) as f:
            workflow_str = f.read()
        self.assertDictEqual(
            {'status': 'ok', 'execution_count': 0, 'payload': [], 'user_expressions': {}},
            kernel.do_execute(workflow_str, False)
        )

    def test_get_past_results(self):
        from cwlkernel.CWLKernel import CWLKernel
        kernel = CWLKernel()
        # cancel send_response
        kernel.send_response = lambda *args, **kwargs: None

        with open(os.sep.join([self.data_directory, 'tar_job.yml'])) as f:
            data = f.read()
        tar_directory = tempfile.gettempdir()
        with open(os.path.join(tar_directory, 'hello.txt'), 'w') as temp_hello_world_file:
            temp_hello_world_file.write("hello world")
        tar_full_name = os.path.join(tar_directory, 'tarfile.tar')
        with tarfile.open(tar_full_name, 'w') as tar:
            tar.add(temp_hello_world_file.name)
        data = data.format(tar_directory=tar_directory)
        result = kernel.do_execute(data, False)
        self.assertEqual('ok', result['status'], f'execution returned an error')

        with open(os.sep.join([self.cwl_directory, 'extract_tar.cwl'])) as f:
            workflow_str = f.read()
        result = kernel.do_execute(workflow_str, False)

        full_path, basename = [(f, os.path.basename(f)) for f in kernel.get_past_results()][0]

        self.assertTrue(full_path.startswith(kernel._results_manager.ROOT_DIRECTORY), 'output is in a wrong directory')
        self.assertTrue(basename, 'hello.txt')

    def test_send_invalid_yaml(self):
        from cwlkernel.CWLKernel import CWLKernel
        kernel = CWLKernel()
        # cancel send_response
        kernel.send_response = lambda *args, **kwargs: None

        invalid_yaml = """
        this is an invalid yaml: fp
        ?: 1
            ?: 2
        ?
        """
        exec_result = kernel.do_execute(invalid_yaml, False)
        self.assertDictEqual({
            'status': 'error',
            # The base class increments the execution count
            'execution_count': 0,
            'payload': [],
            'user_expressions': {},
        }, exec_result)


if __name__ == '__main__':
    unittest.main()
