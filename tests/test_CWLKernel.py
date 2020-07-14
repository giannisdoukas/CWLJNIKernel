import logging
import os
import shutil
import tarfile
import tempfile
import unittest
from io import StringIO
from pathlib import Path

import yaml
from ruamel.yaml import YAML

from cwlkernel.CWLKernel import CONF as KERNEL_CONF
from cwlkernel.CWLKernel import CWLKernel
from cwlkernel.cwlrepository.cwlrepository import WorkflowRepository


class TestCWLKernel(unittest.TestCase):
    data_directory: str
    cwl_directory: str
    kernel_root_directory: str
    maxDiff = None

    def get_kernel(self) -> CWLKernel:
        kernel = CWLKernel()
        # cancel send_response
        kernel.send_response = lambda *args, **kwargs: None
        return kernel

    def setUp(self) -> None:
        import tempfile
        CWLKernel.clear_instance()
        WorkflowRepository(Path(tempfile.mkdtemp()))
        WorkflowRepository.get_instance().delete()

    @classmethod
    def setUpClass(cls) -> None:
        logging.basicConfig(
            level=logging.DEBUG,
            format='%(asctime)-15s:%(levelname)s:%(name)s:%(process)d:%(message)s'
        )
        cls.data_directory = os.sep.join([os.path.dirname(os.path.realpath(__file__)), 'input_data'])
        cls.cwl_directory = os.sep.join([os.path.dirname(os.path.realpath(__file__)), 'cwl'])
        cls.kernel_root_directory = tempfile.mkdtemp()

    def test_get_past_results_from_kernel(self):
        from cwlkernel.CWLKernel import CWLKernel
        kernel = CWLKernel()
        # cancel send_response
        kernel.send_response = lambda *args, **kwargs: None

        def get_data():
            with open(os.sep.join([self.data_directory, 'tar_job.yml'])) as f:
                data = f.read()
            tar_directory = kernel._cwl_executor.file_manager.ROOT_DIRECTORY
            with open(os.path.join(tar_directory, 'hello.txt'), 'w') as temp_hello_world_file:
                temp_hello_world_file.write("hello world")
            tar_full_name = os.path.join(tar_directory, 'tarfile.tar')
            print('create tar file:', tar_full_name)
            with tarfile.open(tar_full_name, 'w') as tar:
                tar.add(temp_hello_world_file.name)
            return data.format(tar_directory=tar_directory), temp_hello_world_file

        data, temp_hello_world_file = get_data()

        with open(os.sep.join([self.cwl_directory, 'extract_tar.cwl'])) as f:
            workflow_str = f.read().format(example_out=temp_hello_world_file.name[1:])
        result = kernel.do_execute(workflow_str, False)
        self.assertEqual('ok', result['status'], f'execution returned an error')

        result = kernel.do_execute(f"% execute extract-tar\n{data}", False)
        self.assertEqual('ok', result['status'], f'execution returned an error')

        full_path, basename = [(f, os.path.basename(f)) for f in kernel.get_past_results()][0]

        self.assertTrue(full_path.startswith(kernel._results_manager.ROOT_DIRECTORY), 'output is in a wrong directory')
        self.assertTrue(basename, 'hello.txt')

        session_dir = kernel._session_dir
        self.assertTrue(os.path.isdir(session_dir))
        kernel.__del__()
        self.assertFalse(os.path.isdir(session_dir))

    def test_get_past_results_without_input(self):
        from cwlkernel.CWLKernel import CWLKernel
        kernel = CWLKernel()
        # cancel send_response
        kernel.send_response = lambda *args, **kwargs: None

        with open(os.sep.join([self.cwl_directory, 'touched.cwl'])) as f:
            workflow_str = f.read()
        self.assertDictEqual(
            {'status': 'ok', 'execution_count': 0, 'payload': [], 'user_expressions': {}},
            kernel.do_execute(workflow_str)
        )
        self.assertEqual(0, len(kernel.get_past_results()))

        self.assertDictEqual(
            {'status': 'ok', 'execution_count': 0, 'payload': [], 'user_expressions': {}},
            kernel.do_execute('% execute touch')
        )

        full_path, basename = [(f, os.path.basename(f)) for f in kernel.get_past_results()][0]

        self.assertTrue(full_path.startswith(kernel._results_manager.ROOT_DIRECTORY), 'output is in a wrong directory')
        self.assertTrue(basename, 'touchedfile.txt')

    def test_execute_echo_cwl(self):
        kernel = self.get_kernel()
        yaml = YAML(typ='safe')

        with open(os.sep.join([self.cwl_directory, 'echo.cwl'])) as f:
            workflow_str = f.read()
        self.assertDictEqual(
            {'status': 'ok', 'execution_count': 0, 'payload': [], 'user_expressions': {}},
            kernel.do_execute(workflow_str, False)
        )
        self.assertIsNotNone(kernel._workflow_repository.get_by_id(yaml.load(workflow_str)['id']))

        with open(os.sep.join([self.data_directory, 'echo-job.yml'])) as f:
            data = '\n'.join(["% execute echo", f.read()])

        self.assertDictEqual(
            {'status': 'ok', 'execution_count': 0, 'payload': [], 'user_expressions': {}},
            kernel.do_execute(data)
        )

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

    def test_handle_input_data_files(self):
        import yaml
        kernel = self.get_kernel()

        with open(os.sep.join([self.data_directory, 'input_with_file.yml'])) as f:
            data = yaml.load(f, Loader=yaml.Loader)
        tmp_dir = tempfile.mkdtemp()
        data['example_file']['location'] = os.path.join(tmp_dir, 'file.txt')
        with open(data['example_file']['location'], 'w') as f:
            f.write('')
        data_stream = StringIO()
        yaml.dump(data, data_stream)

        with open(os.sep.join([self.cwl_directory, 'workflow_with_input_file.cwl'])) as f:
            workflow_str = f.read()

        self.assertDictEqual(
            {'status': 'ok', 'execution_count': 0, 'payload': [], 'user_expressions': {}},
            kernel.do_execute(workflow_str, False)
        )

        self.assertDictEqual(
            {'status': 'ok', 'execution_count': 0, 'payload': [], 'user_expressions': {}},
            kernel.do_execute(f'% execute workflow-with-input-file\n{data_stream.getvalue()}')
        )

        import uuid
        input_with_missing_file = StringIO()
        yaml.dump({"missing_file": {"class": "File", "location": f"/{uuid.uuid4()}"}}, input_with_missing_file)
        response = kernel.do_execute(f'% execute workflow-with-input-file\n{input_with_missing_file.getvalue()}')
        self.assertDictEqual(
            {'status': 'error', 'execution_count': 0, 'payload': [], 'user_expressions': {}},
            response
        )

    def test_send_workflow_without_id(self):
        from cwlkernel.CWLKernel import CWLKernel
        kernel = CWLKernel()
        # cancel send_response
        responses = []
        kernel.send_response = lambda *args, **kwargs: responses.append((args, kwargs))

        with open(os.sep.join([self.cwl_directory, 'without_id.cwl'])) as f:
            workflow_str = f.read()
        self.assertDictEqual(
            {'status': 'ok', 'execution_count': 0, 'payload': [], 'user_expressions': {}},
            kernel.do_execute(workflow_str)
        )
        self.assertRegex(
            responses[-1][0][2]['text'],
            r"^tool '[a-zA-Z0-9-]+' registered"
        )

        with open(os.sep.join([self.cwl_directory, 'echo.cwl'])) as f:
            workflow_str = f.read()
        self.assertDictEqual(
            {'status': 'ok', 'execution_count': 0, 'payload': [], 'user_expressions': {}},
            kernel.do_execute(workflow_str)
        )

        self.assertTupleEqual(
            ((None, 'stream', {'name': 'stdout', 'text': "tool 'echo' registered"}),
             {}),
            responses[-1]
        )

    def test_array_output(self):
        from cwlkernel.CWLKernel import CWLKernel
        kernel = CWLKernel()
        # cancel send_response
        kernel.send_response = lambda *args, **kwargs: None
        with open(os.sep.join([self.cwl_directory, 'array-outputs.cwl'])) as f:
            workflow_str = f.read()
        with open(os.sep.join([self.data_directory, 'array-outputs-job.yml'])) as f:
            data = f"% execute touch\n{f.read()}"
        self.assertDictEqual(
            {'status': 'ok', 'execution_count': 0, 'payload': [], 'user_expressions': {}},
            kernel.do_execute(workflow_str)
        )
        self.assertDictEqual(
            {'status': 'ok', 'execution_count': 0, 'payload': [], 'user_expressions': {}},
            kernel.do_execute(data)
        )

    def test_execute_multiple_steps(self):
        kernel = CWLKernel()
        # cancel send_response
        responses = []
        kernel.send_response = lambda *args, **kwargs: responses.append((args, kwargs))

        with open(os.sep.join([self.cwl_directory, 'head.cwl'])) as f:
            head_cwl = f.read()
        with open(os.sep.join([self.cwl_directory, 'tail.cwl'])) as f:
            tail = f.read()

        self.assertDictEqual(
            {'status': 'ok', 'execution_count': 0, 'payload': [], 'user_expressions': {}},
            kernel.do_execute(head_cwl)
        )
        self.assertDictEqual(
            {'status': 'ok', 'execution_count': 0, 'payload': [], 'user_expressions': {}},
            kernel.do_execute(tail)
        )

        execute_tail = f"""% execute tail 
tailinput:
    class: File
    location: {os.sep.join([self.data_directory, 'data.csv'])}
number_of_lines: 15"""
        self.assertDictEqual(
            {'status': 'ok', 'execution_count': 0, 'payload': [], 'user_expressions': {}},
            kernel.do_execute(execute_tail)
        )

        execute_head = f"""% execute head
headinput:
    class: File
    $data: tailoutput
number_of_lines: 5        
"""
        self.assertDictEqual(
            {'status': 'ok', 'execution_count': 0, 'payload': [], 'user_expressions': {}},
            kernel.do_execute(execute_head)
        )

    def test_viewTool(self):
        kernel = CWLKernel()
        # cancel send_response
        responses = []
        kernel.send_response = lambda *args, **kwargs: responses.append((args, kwargs))

        with open(os.sep.join([self.cwl_directory, 'echo.cwl'])) as f:
            cwl_string = f.read()

        self.assertDictEqual(
            {'status': 'ok', 'execution_count': 0, 'payload': [], 'user_expressions': {}},
            kernel.do_execute(f"""{cwl_string}""")
        )

        self.assertDictEqual(
            {'status': 'ok', 'execution_count': 0, 'payload': [], 'user_expressions': {}},
            kernel.do_execute(f"""% viewTool x""")
        )
        self.assertEqual(
            "Tool 'x' is not registered",
            responses[-1][0][2]['text']
        )

        self.assertDictEqual(
            {'status': 'ok', 'execution_count': 0, 'payload': [], 'user_expressions': {}},
            kernel.do_execute(f"""% viewTool echo""")
        )

        self.assertDictEqual(
            yaml.load(StringIO(cwl_string), yaml.Loader),
            responses[-1][0][2]['data']['application/json']
        )

    def test_import_users_magic_commands(self):
        import importlib
        import cwlkernel.kernel_magics
        self.assertIsNone(KERNEL_CONF.CWLKERNEL_MAGIC_COMMANDS_DIRECTORY)
        tmp_magic_dir = tempfile.mkdtemp()
        os.environ['CWLKERNEL_MAGIC_COMMANDS_DIRECTORY'] = tmp_magic_dir
        m1_code = os.linesep.join([
            "from cwlkernel.CWLKernel import CWLKernel",
            "@CWLKernel.register_magic()",
            "def m1(*args, **kwards):",
            "\tmsg = 'm1 magic function'",
            "\tprint(msg)",
            "\treturn msg",
        ])
        with open(os.path.join(tmp_magic_dir, 'm1.py'), 'w') as f:
            f.write(m1_code)
        m2_code = os.linesep.join([
            "from cwlkernel.CWLKernel import CWLKernel",
            "@CWLKernel.register_magic()",
            "def m2(*args, **kwards):",
            "\tmsg = 'm2 magic function'",
            "\tprint(msg)",
            "\treturn msg",
        ])
        with open(os.path.join(tmp_magic_dir, 'm2.py'), 'w') as f:
            f.write(m2_code)

        importlib.reload(cwlkernel.CWLKernel)
        importlib.reload(cwlkernel.kernel_magics)

        self.assertIsNone(KERNEL_CONF.CWLKERNEL_MAGIC_COMMANDS_DIRECTORY)
        self.assertIn('m1', cwlkernel.CWLKernel.CWLKernel._magic_commands)
        self.assertIn('m2', cwlkernel.CWLKernel.CWLKernel._magic_commands)

        self.assertEqual(
            'm1 magic function',
            cwlkernel.CWLKernel.CWLKernel._magic_commands['m1']()
        )
        self.assertEqual(
            'm2 magic function',
            cwlkernel.CWLKernel.CWLKernel._magic_commands['m2']()
        )
        os.environ.pop('CWLKERNEL_MAGIC_COMMANDS_DIRECTORY')

    def test_system_magic_command(self):
        kernel = CWLKernel()
        # cancel send_response
        responses = []
        kernel.send_response = lambda *args, **kwargs: responses.append((args, kwargs))
        self.assertDictEqual(
            {'status': 'ok', 'execution_count': 0, 'payload': [], 'user_expressions': {}},
            kernel.do_execute("% system echo 'Hello World'")
        )
        self.assertDictEqual(
            {'name': 'stdout', 'text': 'Hello World\n'},
            responses[-1][0][2],
        )

        self.assertDictEqual(
            {'status': 'ok', 'execution_count': 0, 'payload': [], 'user_expressions': {}},
            kernel.do_execute('% system ls ERROR')
        )

        self.assertEqual(
            'stderr',
            responses[-1][0][2]['name'],
        )

    def test_execute_with_provenance(self):
        kernel = CWLKernel()
        # cancel send_response
        responses = []
        kernel.send_response = lambda *args, **kwargs: responses.append((args, kwargs))

        yaml = YAML(typ='safe')

        with open(os.sep.join([self.cwl_directory, 'echo.cwl'])) as f:
            workflow_str = f.read()
        self.assertDictEqual(
            {'status': 'ok', 'execution_count': 0, 'payload': [], 'user_expressions': {}},
            kernel.do_execute(workflow_str, False)
        )
        self.assertIsNotNone(kernel._workflow_repository.get_by_id(yaml.load(workflow_str)['id']))

        with open(os.sep.join([self.data_directory, 'echo-job.yml'])) as f:
            data = '\n'.join(["% executeWithProvenance echo", f.read()])

        self.assertDictEqual(
            {'status': 'ok', 'execution_count': 0, 'payload': [], 'user_expressions': {}},
            kernel.do_execute(data)
        )

        provenance_directory = list(filter(
            lambda r: 'text' in r[0][2] and "Provenance stored in directory" in r[0][2]['text'],
            responses
        ))[0][0][2]['text'].split()[-1]
        print(provenance_directory)
        self.assertTrue(os.path.isdir(provenance_directory))
        self.assertTrue(os.path.isdir(os.path.join(provenance_directory, 'data')))
        self.assertTrue(os.path.isdir(os.path.join(provenance_directory, 'metadata')))
        self.assertTrue(os.path.isdir(os.path.join(provenance_directory, 'snapshot')))
        self.assertTrue(os.path.isfile(os.path.join(provenance_directory, 'snapshot', 'echo.cwl')))
        self.assertTrue(os.path.isdir(os.path.join(provenance_directory, 'workflow')))
        shutil.rmtree(provenance_directory)


if __name__ == '__main__':
    unittest.main()
