from io import StringIO

import logging
import os
from typing import List, Dict, Optional, Tuple, Union
import re
from ipykernel.kernelbase import Kernel
from ruamel import yaml
from ruamel.yaml import YAML

from cwlkernel.CWLBuilder import CWLSnippetBuilder
from cwlkernel.CWLLogger import CWLLogger
from .CWLExecuteConfigurator import CWLExecuteConfigurator
from .CoreExecutor import CoreExecutor
from .IOManager import IOFileManager
from .cwlrepository.cwlrepository import WorkflowRepository
from .cwlrepository.CWLComponent import WorkflowComponentFactory, WorkflowComponent, CWLWorkflow

logger = logging.Logger('CWLKernel')


class CWLKernel(Kernel):
    implementation = 'CWLKernel'
    implementation_version = '0.1'
    language_version = '1.0'
    language_info = {
        'name': 'yaml',
        'mimetype': 'text/x-cwl',
        'file_extension': '.cwl',
    }
    banner = "Common Workflow Language"

    _magic_commands = frozenset(['execute', 'logs', 'data', 'display_data', 'snippet', 'newWorkflow',
                                 'newWorkflowAddStep', 'newWorkflowAddInput', 'newWorkflowBuild'])

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        conf = CWLExecuteConfigurator()
        self._yaml_input_data: Optional[str] = None
        self._results_manager = IOFileManager(os.sep.join([conf.CWLKERNEL_BOOT_DIRECTORY, 'results']))
        runtime_file_manager = IOFileManager(os.sep.join([conf.CWLKERNEL_BOOT_DIRECTORY, 'runtime_data']))
        self._cwl_executor = CoreExecutor(runtime_file_manager)
        self._pid = (os.getpid(), os.getppid())
        self._cwl_logger = CWLLogger(os.path.join(conf.CWLKERNEL_BOOT_DIRECTORY, 'logs'))
        self._set_process_ids()
        self._cwl_logger.save()
        self._workflow_repository = WorkflowRepository()
        self._snippet_builder = CWLSnippetBuilder()
        self._workflow_composer: Optional[CWLWorkflow] = None

    def _set_process_ids(self):
        self._cwl_logger.process_id = {
            "process_id": os.getpid(),
            "parent_process_id": os.getppid()
        }

    def _code_is_valid_yaml(self, code: str) -> Optional[Dict]:
        yaml = YAML(typ='safe')
        try:
            return yaml.load(code)
        except Exception:
            return None

    def _is_magic_command(self, code: str) -> bool:
        split_code = code.split()
        if len(split_code) < 2:
            return False
        if code.startswith("% ") and code.split()[1] in self._magic_commands:
            return True
        return False

    def do_execute(self, code: str, silent=False, store_history: bool = True,
                   user_expressions=None, allow_stdin: bool = False) -> Dict:
        try:
            if self._is_magic_command(code):
                self._do_execute_magic_command(code)
                return {
                    'status': 'ok',
                    # The base class increments the execution count
                    'execution_count': self.execution_count,
                    'payload': [],
                    'user_expressions': {},
                }
            else:
                dict_code = self._code_is_valid_yaml(code)
                if dict_code is None:
                    self.send_response(
                        self.iopub_socket, 'stream',
                        {'name': 'stderr', 'text': f'Unknown input'}
                    )
                    return {
                        'status': 'error',
                        # The base class increments the execution count
                        'execution_count': self.execution_count,
                        'payload': [],
                        'user_expressions': {},
                    }
                else:
                    status, exception = self._do_execute_yaml(dict_code, code)
                    return {
                        'status': status,
                        # The base class increments the execution count
                        'execution_count': self.execution_count,
                        'payload': [],
                        'user_expressions': {},
                    }
        except Exception as e:
            import traceback
            traceback.print_exc()
            self.send_response(
                self.iopub_socket, 'stream',
                {'name': 'stderr', 'text': f'{type(e).__name__}: {e}'}
            )
            return {
                'status': 'error',
                # The base class increments the execution count
                'execution_count': self.execution_count,
                'payload': [],
                'user_expressions': {},
            }

    def _do_execute_yaml(self, dict_code, code):
        exception = None
        if not self._is_cwl(dict_code):
            raise NotImplementedError()
        else:
            try:
                cwl_component = WorkflowComponentFactory().get_workflow_component(code)
                self._workflow_repository.register_tool(cwl_component)
                self.send_response(
                    self.iopub_socket, 'stream',
                    {'name': 'stdout', 'text': f"tool '{cwl_component.id}' registered"}
                )
            except Exception as e:
                exception = e

        status = 'ok' if exception is None else 'error'
        if exception is not None:
            self.send_response(
                self.iopub_socket, 'stream',
                {'name': 'stderr', 'text': f'{type(exception).__name__}: {exception}'}
            )
        return status, exception

    def _do_execute_magic_command(self, commands: str):
        for command in re.compile(r'^%[ ]+', re.MULTILINE).split(commands):
            command = command.strip()
            if command == '':
                continue
            command = command.split(" ")
            command_name = command[0].strip()
            args = " ".join(command[1:])
            getattr(self, f'_execute_magic_{command_name}')(args)

    def _execute_magic_newWorkflowBuild(self, *args):
        self._send_json_response(self._workflow_composer.to_dict())
        self._workflow_repository.register_tool(self._workflow_composer)
        self._workflow_composer = None

    def _execute_magic_newWorkflowAddInput(self, args: str):
        import yaml as y
        args = args.splitlines()
        step_id, step_in_id = args[0].split()
        input_description = '\n'.join(args[1:])
        input_description = y.load(StringIO(input_description), y.Loader)
        self._workflow_composer.add_input(
            workflow_input=input_description,
            step_id=step_id.strip(),
            in_step_id=step_in_id.strip())

    def _execute_magic_newWorkflowAddStepIn(self, args: str):
        args = args.splitlines()
        step_in_args = args[0].split()
        input_description = '\n'.join(args[1:])
        import yaml as y
        input_description = y.load(StringIO(input_description), y.Loader)
        for input_id, description in input_description.items():
            self._workflow_composer.add_step_in_out(description, input_id, *step_in_args)

    def _execute_magic_newWorkflowAddStep(self, ids: str):
        tool_id, step_id = ids.split()
        tool = self._workflow_repository.get_by_id(tool_id)
        self._workflow_composer.add(tool, step_id)

    def _execute_magic_newWorkflow(self, id: str):
        self._workflow_composer = CWLWorkflow(id)

    def _execute_magic_snippet(self, command: str):
        command = command.splitlines()
        command[0] = command[0].strip()
        y = YAML(typ='rt')
        if command[0] == "add":
            snippet = '\n'.join(command[1:])
            self._snippet_builder.append(snippet)
            current_code = y.load(StringIO(self._snippet_builder.get_current_code()))
        elif command[0] == "build":
            snippet = '\n'.join(command[1:])
            self._snippet_builder.append(snippet)
            workflow = self._snippet_builder.build()
            self._workflow_repository.register_tool(workflow)
            current_code = y.load(StringIO(self._snippet_builder.get_current_code()))
            self._snippet_builder.clear()
        else:
            raise ValueError()
        self._send_json_response(current_code)

    def _execute_magic_execute(self, execute_argument_string: str):
        execute_argument_string = execute_argument_string.splitlines()
        cwl_id = execute_argument_string[0].strip()
        cwl_component: WorkflowComponent = self._workflow_repository.get_by_id(cwl_id)
        self._set_data('\n'.join(execute_argument_string[1:]))
        self._execute_workflow(cwl_component.to_yaml(True))
        self._clear_data()

    def _execute_magic_display_data(self, data_name: str):
        if not isinstance(data_name, str) or len(data_name.split()) == 0:
            self._send_error_response(
                'ERROR: you must select an output to display. Correct format:\n % display_data [output name]'
            )
            return
        results = list(
            filter(lambda item: item[1]['id'] == data_name, self._results_manager.get_files_registry().items()))
        if len(results) != 1:
            self.send_response(self.iopub_socket, 'stream', {'name': 'stderr', 'text': 'Result not found'})
            return
        results = results[0]
        with open(results[0]) as f:
            data = f.read()
        self.send_response(self.iopub_socket, 'stream', {'name': 'stdout', 'text': data})

    def _send_error_response(self, text):
        self.send_response(self.iopub_socket, 'stream', {'name': 'stdout', 'text': text})

    def _send_json_response(self, json_data: Union[Dict, List]):
        self.send_response(
            self.iopub_socket,
            'display_data',
            {
                'data': {
                    'text/plain': '<IPython.core.display.JSON object>',
                    'application/json': json_data
                },
                'metadata': {
                    'application/json': {
                        'expanded': False,
                        'root': 'root'
                    }
                }
            }
        )

    def _execute_magic_logs(self, limit=None):
        logger.error('Execute logs magic command')
        limit_len = len(limit)
        if limit_len == 0:
            limit = None
        if limit_len > 0:
            limit = limit[0]
        if isinstance(limit, str):
            limit = int(limit)
        self.send_response(
            self.iopub_socket,
            'display_data',
            {
                'data': {
                    'text/plain': '<IPython.core.display.JSON object>',
                    'application/json': list(self._cwl_logger.load(limit))
                },
                'metadata': {
                    'application/json': {
                        'expanded': False,
                        'root': 'root'
                    }
                }
            }
        )

    def _execute_magic_data(self, *args):
        data = "<ul>\n" + '\n'.join(
            [f'\t<li><a href="file://{d}" target="_empty">{d}</a></li>' for d in self.get_past_results()]) + "\n</ul>"
        self.send_response(
            self.iopub_socket,
            'display_data',
            {
                'data': {
                    'text/html': data
                },
                'metadata': {
                    'application/json': {
                        'expanded': False,
                        'root': 'root'
                    }
                }
            }
        )

    def _set_data(self, code: str) -> Optional[Exception]:
        if len(code.split()) > 0:
            cwl = self._cwl_executor.file_manager.get_files_uri().path
            self._cwl_executor.validate_input_files(yaml.load(code, Loader=yaml.Loader), cwl)
            self._yaml_input_data = code
            self.send_response(self.iopub_socket, 'stream', {'name': 'stdout', 'text': 'Add data in memory'})

    def _clear_data(self):
        self._yaml_input_data = None

    def _execute_workflow(self, code) -> Optional[Exception]:
        input_data = [self._yaml_input_data] if self._yaml_input_data is not None else []
        self._cwl_executor.set_data(input_data)
        self._cwl_executor.set_workflow(code)
        logger.debug('starting executing workflow ...')
        run_id, results, exception = self._cwl_executor.execute()
        logger.debug(f'\texecution results: {run_id}, {results}, {exception}')
        output_directory_for_that_run = str(run_id)
        for output in results:
            if isinstance(results[output], list):
                for i, output_i in enumerate(results[output]):
                    results[output][i]['id'] = f'{output}_{i + 1}'
                    self._results_manager.append_files(
                        [results[output][i]['location']],
                        output_directory_for_that_run,
                        metadata=results[output][i]
                    )
            else:
                results[output]['id'] = output
                self._results_manager.append_files(
                    [results[output]['location']],
                    output_directory_for_that_run,
                    metadata=results[output]
                )
        self.send_response(
            self.iopub_socket,
            'display_data',
            {
                'data': {
                    'text/plain': '<IPython.core.display.JSON object>',
                    'application/json': results
                },
                'metadata': {
                    'application/json': {
                        'expanded': False,
                        'root': 'root'
                    }
                }
            }
        )
        if exception is not None:
            logger.debug(f'execution error: {exception}')
            self.send_response(self.iopub_socket, 'stream', {'name': 'stderr', 'text': str(exception)})
            return exception

    def get_past_results(self) -> List[str]:
        return self._results_manager.get_files()

    def _is_cwl(self, code: Dict):
        return 'cwlVersion' in code.keys()

    def get_pid(self) -> Tuple[int, int]:
        """
        :return: The process id and his parents id
        """
        return self._pid


if __name__ == '__main__':
    from ipykernel.kernelapp import IPKernelApp

    IPKernelApp.launch_instance(kernel_class=CWLKernel)
