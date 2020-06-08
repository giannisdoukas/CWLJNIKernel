import json
import logging
import os
import tarfile
import tempfile
import unittest
from io import StringIO
from pathlib import Path
from urllib.parse import urlparse

import pandas as pd
import requests
import yaml
from mockito import when, mock
from ruamel.yaml import YAML

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

    def test_display_data_magic_command(self):
        from cwlkernel.CWLKernel import CWLKernel
        kernel = CWLKernel()
        # monitor responses
        responses = []
        kernel.send_response = lambda *args, **kwargs: responses.append((args, kwargs))

        with open(os.sep.join([self.cwl_directory, 'echo_stdout.cwl'])) as f:
            workflow_str = f.read()
        self.assertDictEqual(
            {'status': 'ok', 'execution_count': 0, 'payload': [], 'user_expressions': {}},
            kernel.do_execute(workflow_str, False)
        )

        with open(os.sep.join([self.data_directory, 'echo-job.yml'])) as f:
            data = f"% execute echo\n{f.read()}"
        self.assertDictEqual(
            {'status': 'ok', 'execution_count': 0, 'payload': [], 'user_expressions': {}},
            kernel.do_execute(data, False)
        )

        kernel.do_execute('% display_data')
        self.assertEqual(
            'ERROR: you must select an output to display. Correct format:\n % display_data [output name]',
            responses[-1][0][2]['text']
        )

        kernel.do_execute('% display_data echo_output')
        self.assertEqual(
            'Hello world!\n',
            responses[-1][0][2]['text']
        )

        self.assertDictEqual(
            {'status': 'ok', 'execution_count': 0, 'payload': [], 'user_expressions': {}},
            kernel.do_execute(data, False)
        )
        self.assertEqual(
            {'status': 'ok', 'execution_count': 0, 'payload': [], 'user_expressions': {}},
            kernel.do_execute('% display_data echo_output')
        )
        self.assertEqual(
            'Hello world!\n',
            responses[-1][0][2]['text']
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

    def test_logs_magic_command(self):
        from cwlkernel.CWLKernel import CWLKernel
        kernel = CWLKernel()
        # cancel send_response
        responses = []

        kernel.send_response = lambda *args, **kwargs: responses.extend(args[2]['data']['application/json'])
        exec_response = kernel.do_execute('% logs')
        self.assertDictEqual(
            {"status": "ok", "execution_count": 0, 'payload': [], 'user_expressions': {}},
            exec_response
        )
        exec_response = kernel.do_execute('% logs')
        self.assertDictEqual(
            {"status": "ok", "execution_count": 0, 'payload': [], 'user_expressions': {}},
            exec_response
        )
        number_of_responses = len(responses)
        self.assertEqual(number_of_responses, 2)
        exec_response = kernel.do_execute('% logs 1')
        self.assertDictEqual(
            {"status": "ok", "execution_count": 0, 'payload': [], 'user_expressions': {}},
            exec_response
        )
        self.assertEqual(len(responses), number_of_responses + 1)
        self.assertEqual(
            responses[0]['process_id']['process_id'],
            os.getpid()
        )

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

    def test_all_magic_commands_have_methods(self):
        kernel = CWLKernel()
        for magic_name, magic_function in kernel._magic_commands.items():
            hasattr(magic_function, '__call__')

    def test_display_json_output_after_execution(self):
        from cwlkernel.CWLKernel import CWLKernel
        kernel = CWLKernel()
        # cancel send_response
        responses = []
        kernel.send_response = lambda *args, **kwargs: responses.append((args, kwargs))

        # prepare data
        with open(os.sep.join([self.data_directory, 'tar_job.yml'])) as f:
            data = f.read()
        tar_directory = kernel._cwl_executor.file_manager.ROOT_DIRECTORY
        with open(os.path.join(tar_directory, 'hello.txt'), 'w') as temp_hello_world_file:
            temp_hello_world_file.write("hello world")
        tar_full_name = os.path.join(tar_directory, 'tarfile.tar')
        print('create tar file:', tar_full_name)
        with tarfile.open(tar_full_name, 'w') as tar:
            tar.add(temp_hello_world_file.name)
        data = f"% execute extract-tar\n{data.format(tar_directory=tar_directory)}"

        # set workflow
        with open(os.sep.join([self.cwl_directory, 'extract_tar.cwl'])) as f:
            workflow_str = f.read().format(example_out=temp_hello_world_file.name[1:])

        result = kernel.do_execute(workflow_str, False)
        self.assertEqual('ok', result['status'], f'execution returned an error')

        result = kernel.do_execute(data, False)
        self.assertEqual('ok', result['status'], f'execution returned an error')

        self.assertTupleEqual(
            (None, 'display_data',
             {
                 'data': {
                     'text/plain': json.dumps({
                         'example_out': {
                             'location': f'file://{tar_directory}/hello.txt', 'basename': 'hello.txt',
                             'nameroot': 'hello', 'nameext': '.txt', 'class': 'File',
                             'checksum': 'sha1$2aae6c35c94fcfb415dbe95f408b9ce91ee846ed', 'size': 11,
                             'http://commonwl.org/cwltool#generation': 0,
                             'id': 'example_out',
                             "result_counter": 0
                         }
                     }),
                     'application/json': {
                         'example_out': {
                             'location': f'file://{tar_directory}/hello.txt', 'basename': 'hello.txt',
                             'nameroot': 'hello', 'nameext': '.txt', 'class': 'File',
                             'checksum': 'sha1$2aae6c35c94fcfb415dbe95f408b9ce91ee846ed', 'size': 11,
                             'http://commonwl.org/cwltool#generation': 0,
                             'id': 'example_out',
                             "result_counter": 0
                         }
                     }
                 },
                 'metadata': {
                     'application/json': {
                         'expanded': False,
                         'root': 'root'
                     }
                 }
             }
             ),
            responses[-1][0]
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
    location: {urlparse(responses[-1][0][2]['data']['application/json']['tailoutput']['location']).path}
number_of_lines: 5        
"""
        self.assertDictEqual(
            {'status': 'ok', 'execution_count': 0, 'payload': [], 'user_expressions': {}},
            kernel.do_execute(execute_head)
        )

    def test_snippet_builder(self):
        import yaml
        from cwlkernel.CWLKernel import CWLKernel
        kernel = CWLKernel()
        # cancel send_response
        responses = []
        kernel.send_response = lambda *args, **kwargs: responses.append((args, kwargs))

        with open(os.sep.join([self.cwl_directory, 'echo.cwl'])) as f:
            echo_workflow = f.read().splitlines()
        self.assertDictEqual(
            {'status': 'ok', 'execution_count': 0, 'payload': [], 'user_expressions': {}},
            kernel.do_execute(f"% snippet add\n{os.linesep.join(echo_workflow[:6])}")
        )

        self.assertDictEqual(
            yaml.load(StringIO(os.linesep.join(echo_workflow[:6])), yaml.Loader),
            dict(responses[-1][0][2]['data']['application/json'])
        )

        self.assertDictEqual(
            {'status': 'ok', 'execution_count': 0, 'payload': [], 'user_expressions': {}},
            kernel.do_execute(f"% snippet build\n{os.linesep.join(echo_workflow[6:])}")
        )

        self.assertDictEqual(
            yaml.load(StringIO(os.linesep.join(echo_workflow)), yaml.Loader),
            dict(responses[-1][0][2]['data']['application/json'])
        )

        self.assertDictEqual(
            yaml.load(StringIO(kernel._workflow_repository.__repo__.get_by_id("echo").to_yaml()), yaml.Loader),
            yaml.load(StringIO('\n'.join(echo_workflow)), yaml.Loader),
        )

    def test_compose(self):
        kernel = CWLKernel()
        # cancel send_response
        responses = []
        kernel.send_response = lambda *args, **kwargs: responses.append((args, kwargs))
        with open(os.sep.join([self.cwl_directory, 'head.cwl'])) as f:
            head = f.read()
        with open(os.sep.join([self.cwl_directory, 'tail.cwl'])) as f:
            tail = f.read()
        self.assertDictEqual(
            {'status': 'ok', 'execution_count': 0, 'payload': [], 'user_expressions': {}},
            kernel.do_execute(head)
        )
        self.assertDictEqual(
            {'status': 'ok', 'execution_count': 0, 'payload': [], 'user_expressions': {}},
            kernel.do_execute(tail)
        )

        self.assertDictEqual(
            {'status': 'ok', 'execution_count': 0, 'payload': [], 'user_expressions': {}},
            kernel.do_execute("""% newWorkflow main
% newWorkflowAddStep tail tailstepid
% newWorkflowAddStep head headstepid
% newWorkflowAddInput headstepid headinput
id: inputfile
type: File
% newWorkflowAddStepIn tailstepid headstepid headoutput
tailinput: headstepid/headoutput
% newWorkflowBuild""")
        )

        self.assertDictEqual(
            {
                "cwlVersion": "v1.0",
                "class": "Workflow",
                "id": "main",
                "inputs": [{'id': 'inputfile', 'type': 'File'}],
                "outputs": [],
                "steps": {
                    "headstepid":
                        {
                            "run": "head.cwl",
                            "in": {"headinput": "inputfile"},
                            "out": ['headoutput']
                        },
                    "tailstepid":
                        {
                            "run": "tail.cwl",
                            "in": {"tailinput": "headstepid/headoutput"},
                            "out": []
                        },
                },
                'requirements': {}
            },
            yaml.load(kernel._workflow_repository.get_by_id("main").to_yaml(), yaml.Loader),
        )

        self.assertDictEqual(
            {'status': 'ok', 'execution_count': 0, 'payload': [], 'user_expressions': {}},
            kernel.do_execute(f"""% execute main
inputfile: 
    class: File
    location: {os.path.join(self.data_directory, "data.csv")}""")
        )

    def test_githubImport(self):
        when(requests) \
            .get("https://api.github.com/repos/giannisdoukas/CWLJNIKernel/contents/tests/cwl/head.cwl?ref=dev") \
            .thenReturn(mock({
            'status_code': 200,
            'json': lambda: {
                "name": "head.cwl",
                "path": "tests/cwl/head.cwl",
                "sha": "74e6680835a37ecc696279bd84495a4ec370c732",
                "size": 316,
                "url": "https://api.github.com/repos/giannisdoukas/CWLJNIKernel/contents/tests/cwl/head.cwl?ref=dev",
                "html_url": "https://github.com/giannisdoukas/CWLJNIKernel/blob/dev/tests/cwl/head.cwl",
                "git_url": "https://api.github.com/repos/giannisdoukas/CWLJNIKernel/git/blobs/74e6680835a37ecc696279bd84495a4ec370c732",
                "download_url": "https://raw.githubusercontent.com/giannisdoukas/CWLJNIKernel/dev/tests/cwl/head.cwl",
                "type": "file",
                "content": "Y2xhc3M6IENvbW1hbmRMaW5lVG9vbApjd2xWZXJzaW9uOiB2MS4wCmlkOiBo\nZWFkCmJhc2VDb21tYW5kOgogIC0gaGVhZAppbnB1dHM6CiAgLSBpZDogbnVt\nYmVyX29mX2xpbmVzCiAgICB0eXBlOiBpbnQ/CiAgICBpbnB1dEJpbmRpbmc6\nCiAgICAgIHBvc2l0aW9uOiAwCiAgICAgIHByZWZpeDogJy1uJwogIC0gaWQ6\nIGhlYWRpbnB1dAogICAgdHlwZTogRmlsZQogICAgaW5wdXRCaW5kaW5nOgog\nICAgICBwb3NpdGlvbjogMQpvdXRwdXRzOgogIC0gaWQ6IGhlYWRvdXRwdXQK\nICAgIHR5cGU6IHN0ZG91dApsYWJlbDogaGVhZApzdGRvdXQ6IGhlYWQub3V0\nCg==\n",
                "encoding": "base64",
                "_links": {
                    "self": "https://api.github.com/repos/giannisdoukas/CWLJNIKernel/contents/tests/cwl/head.cwl?ref=dev",
                    "git": "https://api.github.com/repos/giannisdoukas/CWLJNIKernel/git/blobs/74e6680835a37ecc696279bd84495a4ec370c732",
                    "html": "https://github.com/giannisdoukas/CWLJNIKernel/blob/dev/tests/cwl/head.cwl"
                }
            }
        }))
        when(requests) \
            .get("https://api.github.com/repos/giannisdoukas/CWLJNIKernel/contents/tests/cwl/3stepWorkflow.cwl?ref=dev") \
            .thenReturn(mock(
            {
                'status_code': 200,
                'json': lambda: {
                    "name": "3stepWorkflow.cwl",
                    "path": "tests/cwl/3stepWorkflow.cwl",
                    "sha": "681de5be2005ab7258c33328140b33e0c42b891f",
                    "size": 810,
                    "url": "https://api.github.com/repos/giannisdoukas/CWLJNIKernel/contents/tests/cwl/3stepWorkflow.cwl?ref=dev",
                    "html_url": "https://github.com/giannisdoukas/CWLJNIKernel/blob/dev/tests/cwl/3stepWorkflow.cwl",
                    "git_url": "https://api.github.com/repos/giannisdoukas/CWLJNIKernel/git/blobs/681de5be2005ab7258c33328140b33e0c42b891f",
                    "download_url": "https://raw.githubusercontent.com/giannisdoukas/CWLJNIKernel/dev/tests/cwl/3stepWorkflow.cwl",
                    "type": "file",
                    "content": "IyEvdXNyL2Jpbi9lbnYgY3dsdG9vbApjd2xWZXJzaW9uOiB2MS4wCmNsYXNz\nOiBXb3JrZmxvdwppZDogdGhyZWVzdGVwcwppbnB1dHM6CiAgLSBpZDogaW5w\ndXRmaWxlCiAgICB0eXBlOiBGaWxlCiAgLSBpZDogcXVlcnkKICAgIHR5cGU6\nIHN0cmluZwpvdXRwdXRzOgogIG91dHB1dGZpbGU6CiAgICB0eXBlOiBGaWxl\nCiAgICBvdXRwdXRTb3VyY2U6IGdyZXAyL2dyZXBvdXRwdXQKICBvdXRwdXRm\naWxlMjoKICAgIHR5cGU6IEZpbGUKICAgIG91dHB1dFNvdXJjZTogZ3JlcHN0\nZXAvZ3JlcG91dHB1dAoKc3RlcHM6CiAgaGVhZDoKICAgIHJ1bjogaGVhZC5j\nd2wKICAgIGluOgogICAgICBoZWFkaW5wdXQ6IGlucHV0ZmlsZQogICAgb3V0\nOiBbaGVhZG91dHB1dF0KCiAgZ3JlcHN0ZXA6CiAgICBydW46IGdyZXAuY3ds\nCiAgICBpbjoKICAgICAgZ3JlcGlucHV0OiBoZWFkL2hlYWRvdXRwdXQKICAg\nICAgcXVlcnk6IHF1ZXJ5CiAgICAgIGxpbmVzX2JlbGxvdzoKICAgICAgICB2\nYWx1ZUZyb206ICR7cmV0dXJuIDU7fQogICAgb3V0OiBbZ3JlcG91dHB1dF0K\nICBncmVwMjoKICAgIHJ1bjogZ3JlcC5jd2wKICAgIGluOgogICAgICBncmVw\naW5wdXQ6IGdyZXBzdGVwL2dyZXBvdXRwdXQKICAgICAgcXVlcnk6CiAgICAg\nICAgdmFsdWVGcm9tOiAncXVlcnknCiAgICAgIGxpbmVzX2Fib3ZlOgogICAg\nICAgIHZhbHVlRnJvbTogJHtyZXR1cm4gNTt9CiAgICBvdXQ6IFtncmVwb3V0\ncHV0XQpyZXF1aXJlbWVudHM6CiAgU3RlcElucHV0RXhwcmVzc2lvblJlcXVp\ncmVtZW50OiB7fQogIElubGluZUphdmFzY3JpcHRSZXF1aXJlbWVudDoge30K\n",
                    "encoding": "base64",
                    "_links": {
                        "self": "https://api.github.com/repos/giannisdoukas/CWLJNIKernel/contents/tests/cwl/3stepWorkflow.cwl?ref=dev",
                        "git": "https://api.github.com/repos/giannisdoukas/CWLJNIKernel/git/blobs/681de5be2005ab7258c33328140b33e0c42b891f",
                        "html": "https://github.com/giannisdoukas/CWLJNIKernel/blob/dev/tests/cwl/3stepWorkflow.cwl"
                    }
                }
            }))
        when(requests) \
            .get("https://api.github.com/repos/giannisdoukas/CWLJNIKernel/contents/tests/cwl/grep.cwl?ref=dev") \
            .thenReturn(mock(
            {
                'status_code': 200,
                'json': lambda: {
                    "name": "grep.cwl",
                    "path": "tests/cwl/grep.cwl",
                    "sha": "a0ce6c241f90eafd0b4c489a1880368f2ceca1d9",
                    "size": 476,
                    "url": "https://api.github.com/repos/giannisdoukas/CWLJNIKernel/contents/tests/cwl/grep.cwl?ref=dev",
                    "html_url": "https://github.com/giannisdoukas/CWLJNIKernel/blob/dev/tests/cwl/grep.cwl",
                    "git_url": "https://api.github.com/repos/giannisdoukas/CWLJNIKernel/git/blobs/a0ce6c241f90eafd0b4c489a1880368f2ceca1d9",
                    "download_url": "https://raw.githubusercontent.com/giannisdoukas/CWLJNIKernel/dev/tests/cwl/grep.cwl",
                    "type": "file",
                    "content": "Y2xhc3M6IENvbW1hbmRMaW5lVG9vbApjd2xWZXJzaW9uOiB2MS4wCmlkOiBn\ncmVwCmJhc2VDb21tYW5kOgogIC0gZ3JlcAppbnB1dHM6CiAgLSBpZDogcXVl\ncnkKICAgIHR5cGU6IHN0cmluZwogICAgaW5wdXRCaW5kaW5nOgogICAgICBw\nb3NpdGlvbjogMAogIC0gaWQ6IGxpbmVzX2JlbGxvdwogICAgdHlwZTogaW50\nPwogICAgaW5wdXRCaW5kaW5nOgogICAgICBwb3NpdGlvbjogMQogICAgICBw\ncmVmaXg6ICctQScKICAtIGlkOiBsaW5lc19hYm92ZQogICAgdHlwZTogaW50\nPwogICAgaW5wdXRCaW5kaW5nOgogICAgICBwb3NpdGlvbjogMgogICAgICBw\ncmVmaXg6ICctQicKICAtIGlkOiBncmVwaW5wdXQKICAgIHR5cGU6IEZpbGUK\nICAgIGlucHV0QmluZGluZzoKICAgICAgcG9zaXRpb246IDEwCm91dHB1dHM6\nCiAgLSBpZDogZ3JlcG91dHB1dAogICAgdHlwZTogc3Rkb3V0CmxhYmVsOiBo\nZWFkCnN0ZG91dDogZ3JlcG91dHB1dC5vdXQ=\n",
                    "encoding": "base64",
                    "_links": {
                        "self": "https://api.github.com/repos/giannisdoukas/CWLJNIKernel/contents/tests/cwl/grep.cwl?ref=dev",
                        "git": "https://api.github.com/repos/giannisdoukas/CWLJNIKernel/git/blobs/a0ce6c241f90eafd0b4c489a1880368f2ceca1d9",
                        "html": "https://github.com/giannisdoukas/CWLJNIKernel/blob/dev/tests/cwl/grep.cwl"
                    }
                }
            }
        ))
        kernel = CWLKernel()
        # cancel send_response
        responses = []
        kernel.send_response = lambda *args, **kwargs: responses.append((args, kwargs))
        self.assertDictEqual(
            {'status': 'ok', 'execution_count': 0, 'payload': [], 'user_expressions': {}},
            kernel.do_execute(
                "% githubImport https://github.com/giannisdoukas/CWLJNIKernel/blob/dev/tests/cwl/3stepWorkflow.cwl")
        )

        self.assertDictEqual(
            {'status': 'ok', 'execution_count': 0, 'payload': [], 'user_expressions': {}},
            kernel.do_execute(f"""% execute threesteps
inputfile:
    class: File
    location: {os.sep.join([self.cwl_directory, '3stepWorkflow.cwl'])}
query: id""")
        )

    def test_githubImport_without_id(self):
        when(requests) \
            .get("https://api.github.com/repos/giannisdoukas/CWLJNIKernel/contents/tests/cwl/without_id.cwl?ref=dev") \
            .thenReturn(mock({
            'status_code': 200,
            'json': lambda: {
                "name": "without_id.cwl",
                "path": "tests/cwl/without_id.cwl",
                "sha": "8dd9d522c666d469c75bac566957e78acdb4a5f6",
                "size": 129,
                "url": "https://api.github.com/repos/giannisdoukas/CWLJNIKernel/contents/tests/cwl/without_id.cwl?ref=dev",
                "html_url": "https://github.com/giannisdoukas/CWLJNIKernel/blob/dev/tests/cwl/without_id.cwl",
                "git_url": "https://api.github.com/repos/giannisdoukas/CWLJNIKernel/git/blobs/8dd9d522c666d469c75bac566957e78acdb4a5f6",
                "download_url": "https://raw.githubusercontent.com/giannisdoukas/CWLJNIKernel/dev/tests/cwl/without_id.cwl",
                "type": "file",
                "content": "Y3dsVmVyc2lvbjogdjEuMApjbGFzczogQ29tbWFuZExpbmVUb29sCmJhc2VD\nb21tYW5kOiBbZWNobywgImhlbGxvIHdvcmxkIl0KaW5wdXRzOiBbXQpvdXRw\ndXRzOgogIGV4YW1wbGVfb3V0cHV0OgogICAgdHlwZTogc3Rkb3V0\n",
                "encoding": "base64",
                "_links": {
                    "self": "https://api.github.com/repos/giannisdoukas/CWLJNIKernel/contents/tests/cwl/without_id.cwl?ref=dev",
                    "git": "https://api.github.com/repos/giannisdoukas/CWLJNIKernel/git/blobs/8dd9d522c666d469c75bac566957e78acdb4a5f6",
                    "html": "https://github.com/giannisdoukas/CWLJNIKernel/blob/dev/tests/cwl/without_id.cwl"
                }
            }}))

        kernel = CWLKernel()
        # cancel send_response
        responses = []
        kernel.send_response = lambda *args, **kwargs: responses.append((args, kwargs))
        self.assertDictEqual(
            {'status': 'ok', 'execution_count': 0, 'payload': [], 'user_expressions': {}},
            kernel.do_execute(
                "% githubImport https://github.com/giannisdoukas/CWLJNIKernel/blob/dev/tests/cwl/without_id.cwl")
        )
        self.assertRegex(responses[-1][0][2]['text'], r"^tool '[a-zA-Z0-9-]+' registered")

        self.assertDictEqual(
            {'status': 'ok', 'execution_count': 0, 'payload': [], 'user_expressions': {}},
            kernel.do_execute(f"""% execute {responses[-1][0][2]['text'].split("'")[1]}""")
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

    def test_display_data_csv(self):
        kernel = CWLKernel()
        # cancel send_response
        responses = []
        kernel.send_response = lambda *args, **kwargs: responses.append((args, kwargs))

        self.assertDictEqual(
            {'status': 'ok', 'execution_count': 0, 'payload': [], 'user_expressions': {}},
            kernel.do_execute(f"""% display_data_csv no-existing""")
        )
        self.assertEqual(
            'Result not found',
            responses[-1][0][2]['text']
        )

        with open(os.sep.join([self.cwl_directory, 'head.cwl'])) as f:
            head = f.read()
        self.assertDictEqual(
            {'status': 'ok', 'execution_count': 0, 'payload': [], 'user_expressions': {}},
            kernel.do_execute(head)
        )

        self.assertDictEqual(
            {'status': 'ok', 'execution_count': 0, 'payload': [], 'user_expressions': {}},
            kernel.do_execute(f"""% execute head 
headinput:
    class: File
    location: {os.sep.join([self.data_directory, 'data.csv'])}
number_of_lines: 15""")
        )

        self.assertDictEqual(
            {'status': 'ok', 'execution_count': 0, 'payload': [], 'user_expressions': {}},
            kernel.do_execute("% display_data_csv headoutput")
        )

        self.assertListEqual(
            [-54, -85, -5, 47, 39, 20, -58, 24, 12, 13, 4, -22, -1, -70, 44, -30, 91, -6, 40, -24],
            list(pd.read_html(responses[-1][0][2]['data']['text/html'], header=None)[0].values[0])
        )

    def test_sample_csv(self):
        self.assertTrue(False)


if __name__ == '__main__':
    unittest.main()
