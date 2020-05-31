import json
import logging
import os
import re
import traceback
from pathlib import Path
from typing import List, Dict, Optional, Tuple, Union, Callable

from ipykernel.kernelbase import Kernel
from ruamel import yaml
from ruamel.yaml import YAML

from cwlkernel.CWLBuilder import CWLSnippetBuilder
from cwlkernel.CWLLogger import CWLLogger
from .CWLExecuteConfigurator import CWLExecuteConfigurator
from .CoreExecutor import CoreExecutor
from .IOManager import IOFileManager
from .cwlrepository.CWLComponent import WorkflowComponentFactory, CWLWorkflow
from .cwlrepository.cwlrepository import WorkflowRepository

logger = logging.Logger('CWLKernel')


class CWLKernel(Kernel):
    """
    Jupyter Notebook kernel for CWL
    """
    implementation = 'CWLKernel'
    implementation_version = '0.1'
    language_version = '1.0'
    language_info = {
        'name': 'yaml',
        'mimetype': 'text/x-cwl',
        'file_extension': '.cwl',
    }
    banner = "Common Workflow Language"

    _magic_commands: Dict = {}

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        conf = CWLExecuteConfigurator()
        self._yaml_input_data: Optional[str] = None
        self._results_manager = IOFileManager(os.sep.join([conf.CWLKERNEL_BOOT_DIRECTORY, self.ident, 'results']))
        runtime_file_manager = IOFileManager(os.sep.join([conf.CWLKERNEL_BOOT_DIRECTORY, self.ident, 'runtime_data']))
        self._cwl_executor = CoreExecutor(runtime_file_manager)
        self._pid = (os.getpid(), os.getppid())
        self._cwl_logger = CWLLogger(os.path.join(conf.CWLKERNEL_BOOT_DIRECTORY, self.ident, 'logs'))
        self._set_process_ids()
        self._cwl_logger.save()
        self._workflow_repository = WorkflowRepository(
            Path(os.sep.join([conf.CWLKERNEL_BOOT_DIRECTORY, self.ident, 'repo'])))
        self._snippet_builder = CWLSnippetBuilder()
        self._workflow_composer: Optional[CWLWorkflow] = None

    @staticmethod
    def register_magic(magic: Callable):
        CWLKernel._magic_commands[magic.__name__] = magic
        return magic

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
                status = 'ok'
            else:
                dict_code = self._code_is_valid_yaml(code)
                if dict_code is None:
                    raise RuntimeError('Input cannot be parsed')
                else:
                    status, exception = self._do_execute_yaml(dict_code, code)
                    if exception is not None:
                        traceback.print_exc()
                        self.send_response(
                            self.iopub_socket, 'stream',
                            {'name': 'stderr', 'text': f'{type(exception).__name__}: {exception}'}
                        )
        except Exception as e:
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
        return {
            'status': status,
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
            self._magic_commands[command_name](self, args)

    def _send_error_response(self, text):
        self.send_response(self.iopub_socket, 'stream', {'name': 'stdout', 'text': text})

    def _send_json_response(self, json_data: Union[Dict, List]):
        self.send_response(
            self.iopub_socket,
            'display_data',
            {
                'data': {
                    'text/plain': json.dumps(json_data),
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

    def _set_data(self, code: str) -> Optional[Exception]:
        if len(code.split()) > 0:
            cwl = self._cwl_executor.file_manager.get_files_uri().path
            self._cwl_executor.validate_input_files(yaml.load(code, Loader=yaml.Loader), cwl)
            self._yaml_input_data = code
            self.send_response(self.iopub_socket, 'stream', {'name': 'stdout', 'text': 'Add data in memory'})

    def _clear_data(self):
        self._yaml_input_data = None

    def _execute_workflow(self, code_path: Path) -> Optional[Exception]:
        input_data = [self._yaml_input_data] if self._yaml_input_data is not None else []
        self._cwl_executor.set_data(input_data)
        self._cwl_executor.set_workflow_path(str(code_path))
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
        self._send_json_response(results)
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
