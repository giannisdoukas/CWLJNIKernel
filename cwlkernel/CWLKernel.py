import json
import logging
import os
from typing import List, Dict, Optional, Tuple

from ipykernel.kernelbase import Kernel
from ruamel.yaml import YAML

from cwlkernel.CWLLogger import CWLLogger
from cwlkernel.CWLLoggerStorageManager import CWLLoggerStorageManager
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

    _magic_commands = frozenset(['logs'])

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

        exception = None

        if not self._is_cwl(dict_code):
            self._accumulate_data(code)
        else:
            exception = self._execute_workflow(code)

        status = 'ok' if exception is None else 'error'
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

    def _execute_magic_logs(self, limit=None):
        logger.error('Execute logs magic command')
        i = 0
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
        return i

    def _accumulate_data(self, code):
        self._yaml_input_data.append(code)
        self.send_response(self.iopub_socket, 'stream', {'name': 'stdout', 'text': 'Add data in memory'})

    def _execute_workflow(self, code) -> Optional[Exception]:
        self._cwl_executor.set_data(self._yaml_input_data)
        self._cwl_executor.set_workflow(code)
        logger.debug('starting executing workflow ...')
        run_id, new_files, stdout, stderr, exception = self._cwl_executor.execute()
        logger.debug(f'\texecution results: {run_id}, {new_files}, {stdout}, {stderr}, {exception}')
        output_directory_for_that_run = str(run_id)
        self._results_manager.append_files(new_files, output_directory_for_that_run)
        stdout = stdout.getvalue()
        stderr = stderr.getvalue()
        if len(stdout) > 0:
            logger.debug(f'execute stdout: {stdout}')
            self.send_response(self.iopub_socket, 'stream', {'name': 'stdout', 'text': stdout})
        if len(stderr) > 0:
            logger.debug(f'execute stderr: {stderr}')
            self.send_response(self.iopub_socket, 'stream', {'name': 'stderr', 'text': stderr})
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
