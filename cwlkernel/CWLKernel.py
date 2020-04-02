import logging
import os
from typing import List, Dict, Optional, Tuple, Union

from ipykernel.kernelbase import Kernel
from ruamel import yaml
from ruamel.yaml import YAML

from cwlkernel.CWLLogger import CWLLogger
from .CWLExecuteConfigurator import CWLExecuteConfigurator
from .CoreExecutor import CoreExecutor
from .IOManager import IOFileManager

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

    _magic_commands = frozenset(['logs', 'data', 'display_data'])

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        conf = CWLExecuteConfigurator()
        self._yaml_input_data: List[str] = []
        self._results_manager = IOFileManager(os.sep.join([conf.CWLKERNEL_BOOT_DIRECTORY, 'results']))
        runtime_file_manager = IOFileManager(os.sep.join([conf.CWLKERNEL_BOOT_DIRECTORY, 'runtime_data']))
        self._cwl_executor = CoreExecutor(runtime_file_manager)
        self._pid = (os.getpid(), os.getppid())
        self._cwl_logger = CWLLogger(os.path.join(conf.CWLKERNEL_BOOT_DIRECTORY, 'logs'))
        self._set_process_ids()
        self._cwl_logger.save()

    def _set_process_ids(self):
        self._cwl_logger.process_id = {
            "process_id": os.getpid(),
            "parent_process_id": os.getppid()
        }

    def _code_is_valid_yaml(self, code) -> Optional[Dict]:
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
        if self._is_magic_command(code):
            self._execute_magic_command(code)
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
                return {
                    'status': 'error',
                    # The base class increments the execution count
                    'execution_count': self.execution_count,
                    'payload': [],
                    'user_expressions': {},
                }

        if not self._is_cwl(dict_code):
            exception = self._accumulate_data(code)
        else:
            exception = self._execute_workflow(code)
            self._clear_data()

        status = 'ok' if exception is None else 'error'
        if exception is not None:
            self.send_response(
                self.iopub_socket, 'stream',
                {'name': 'stderr', 'text': f'{type(exception).__name__}: {exception}'}
            )
        return {
            'status': status,
            # The base class increments the execution count
            'execution_count': self.execution_count,
            'payload': [],
            'user_expressions': {},
        }

    def _execute_magic_command(self, command: str):
        command = command.split()[1:]
        command_name = command[0]
        args = command[1:]
        getattr(self, f'_execute_magic_{command_name}')(args)

    def _execute_magic_display_data(self, data_name):
        if len(data_name) != 1 or not isinstance(data_name[0], str):
            self._send_error_response('ERROR: you must select an output to display. Correct format:\n % display_data [output name]')
            return
        results = list(filter(lambda item: item[1]['id'] == data_name[0], self._results_manager.get_files_registry().items()))
        if len(results) != 1:
            self.send_response(self.iopub_socket, 'stream', {'name': 'stderr', 'text': 'Result not found'})
            return
        results = results[0]
        with open(results[0]) as f:
            data = f.read()
        self.send_response(self.iopub_socket, 'stream', {'name': 'stdout', 'text': data})

    def _send_error_response(self, text):
        self.send_response(self.iopub_socket, 'stream', {'name': 'stdout', 'text': text})

    def _send_json_response(self, json_data: Union[Dict,List]):
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

    def _accumulate_data(self, code: str) -> Optional[Exception]:
        cwl = self._cwl_executor.file_manager.get_files_uri().path
        try:
            self._cwl_executor.validate_input_files(yaml.load(code, Loader=yaml.Loader), cwl)
        except FileNotFoundError as e:
            return e
        self._yaml_input_data.append(code)
        self.send_response(self.iopub_socket, 'stream', {'name': 'stdout', 'text': 'Add data in memory'})

    def _clear_data(self):
        self._yaml_input_data = []

    def _execute_workflow(self, code) -> Optional[Exception]:
        self._cwl_executor.set_data(self._yaml_input_data)
        self._cwl_executor.set_workflow(code)
        logger.debug('starting executing workflow ...')
        run_id, results, stdout, stderr, exception = self._cwl_executor.execute()
        logger.debug(f'\texecution results: {run_id}, {results}, {stdout}, {stderr}, {exception}')
        output_directory_for_that_run = str(run_id)
        for output in results:
            if isinstance(results[output], list):
                for i, output_i in enumerate(results[output]):
                    results[output][i]['id'] = f'{output}_{i+1}'
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
