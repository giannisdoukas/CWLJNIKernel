import json
import logging
import os
import re
import traceback
from io import StringIO
from pathlib import Path
from typing import List, Dict, Optional, Tuple, Union, Callable, NoReturn

from ipykernel.kernelbase import Kernel
from ruamel import yaml
from ruamel.yaml import YAML

from .AutoCompleteEngine import AutoCompleteEngine
from .CWLBuilder import CWLSnippetBuilder
from .CWLExecuteConfigurator import CWLExecuteConfigurator
from .CWLLogger import CWLLogger
from .CoreExecutor import CoreExecutor
from .IOManager import IOFileManager, ResultsManager
from .cwlrepository.CWLComponent import WorkflowComponentFactory, CWLWorkflow
from .cwlrepository.cwlrepository import WorkflowRepository
from .git.CWLGitResolver import CWLGitResolver

version = "0.0.2"

CONF = CWLExecuteConfigurator()


class CWLKernel(Kernel):
    """Jupyter Notebook kernel for CWL."""
    implementation = 'CWLKernel'
    implementation_version = version
    language_version = '1.1'
    language_info = {
        'name': 'yaml',
        'mimetype': 'text/x-cwl',
        'file_extension': '.cwl',
    }
    banner = "Common Workflow Language"

    _magic_commands: Dict = {}
    _auto_complete_engine = AutoCompleteEngine(_magic_commands)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._yaml_input_data: Optional[str] = None
        self._results_manager = ResultsManager(os.sep.join([CONF.CWLKERNEL_BOOT_DIRECTORY, self.ident, 'results']))
        runtime_file_manager = IOFileManager(os.sep.join([CONF.CWLKERNEL_BOOT_DIRECTORY, self.ident, 'runtime_data']))
        self._cwl_executor = CoreExecutor(runtime_file_manager)
        self._pid = (os.getpid(), os.getppid())
        self._cwl_logger = CWLLogger(os.path.join(CONF.CWLKERNEL_BOOT_DIRECTORY, self.ident, 'logs'))
        self._set_process_ids()
        self._cwl_logger.save()
        self._workflow_repository = WorkflowRepository(
            Path(os.sep.join([CONF.CWLKERNEL_BOOT_DIRECTORY, self.ident, 'repo'])))
        self._snippet_builder = CWLSnippetBuilder()
        self._workflow_composer: Optional[CWLWorkflow] = None
        self._github_resolver: CWLGitResolver = CWLGitResolver(
            Path(os.sep.join([CONF.CWLKERNEL_BOOT_DIRECTORY, self.ident, 'git'])))
        if self.log is None:
            self.log = logging.getLogger()

    @classmethod
    def register_magic(cls, magic: Callable):
        cls._magic_commands[magic.__name__] = magic
        cls._auto_complete_engine.add_magic_command(magic.__name__)
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
        status = 'ok'
        try:
            if self._is_magic_command(code):
                self._do_execute_magic_command(code)
            else:
                dict_code = self._code_is_valid_yaml(code)
                if dict_code is None:
                    raise RuntimeError('Input cannot be parsed')
                else:
                    self._do_execute_yaml(dict_code, code)
        except Exception as e:
            status = 'error'
            traceback.print_exc()
            self._send_error_response(f'{type(e).__name__}: {e}')
        finally:
            return {
                'status': status,
                # The base class increments the execution count
                'execution_count': self.execution_count,
                'payload': [],
                'user_expressions': {},
            }

    def _do_execute_yaml(self, dict_code, code):
        if not self._is_cwl(dict_code):
            raise NotImplementedError()
        else:
            cwl_component = WorkflowComponentFactory().get_workflow_component(code)
            self._workflow_repository.register_tool(cwl_component)
            self.send_response(
                self.iopub_socket, 'stream',
                {'name': 'stdout', 'text': f"tool '{cwl_component.id}' registered"}
            )

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
        self.send_response(self.iopub_socket, 'stream', {'name': 'stderr', 'text': text})

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

    def _set_data(self, code: str) -> NoReturn:
        if len(code.split()) > 0:
            cwd = Path(self._cwl_executor.file_manager.get_files_uri().path)
            data = self._preprocess_data(yaml.load(code, Loader=yaml.Loader))
            self._cwl_executor.validate_input_files(data, cwd)
            code_stream = StringIO()
            yaml.safe_dump(data, code_stream)
            self._yaml_input_data = code_stream.getvalue()
            self.send_response(self.iopub_socket, 'stream', {'name': 'stdout', 'text': 'Add data in memory'})

    def _preprocess_data(self, data: Dict) -> Dict:
        """
        On the execution the user can reference the data id of a file instead of the actual path. That function
        apply that logic

        @param data: the actual data
        @return the data after the transformation
        """

        has_change = False
        for key_id in data:
            if isinstance(data[key_id], dict) and \
                    'class' in data[key_id] and \
                    data[key_id]['class'] == 'File' and \
                    '$data' in data[key_id]:
                has_change = True
                data[key_id]['location'] = self._results_manager.get_last_result_by_id(data[key_id]["$data"])
                data[key_id].pop('$data')
        if has_change is True:
            self.send_text_to_stdout('set data to:\n')
            self._send_json_response(data)
        return data

    def _clear_data(self):
        self._yaml_input_data = None

    def _execute_workflow(self, code_path: Path) -> Optional[Exception]:
        input_data = [self._yaml_input_data] if self._yaml_input_data is not None else []
        self._cwl_executor.set_data(input_data)
        self._cwl_executor.set_workflow_path(str(code_path))
        self.log.debug('starting executing workflow ...')
        run_id, results, exception = self._cwl_executor.execute()
        self.log.debug(f'\texecution results: {run_id}, {results}, {exception}')
        output_directory_for_that_run = str(run_id)
        for output in results:
            if isinstance(results[output], list):
                for i, _ in enumerate(results[output]):
                    results[output][i]['id'] = f'{output}_{i + 1}'
                    results[output][i]['result_counter'] = self._results_manager.files_counter
                    self._results_manager.append_files(
                        [results[output][i]['location']],
                        output_directory_for_that_run,
                        metadata=results[output][i]
                    )
            else:
                results[output]['id'] = output
                results[output]['result_counter'] = self._results_manager.files_counter
                self._results_manager.append_files(
                    [results[output]['location']],
                    output_directory_for_that_run,
                    metadata=results[output]
                )
        self._send_json_response(results)
        if exception is not None:
            self.log.debug(f'execution error: {exception}')
            self.send_response(self.iopub_socket, 'stream', {'name': 'stderr', 'text': str(exception)})
            return exception

    def get_past_results(self) -> List[str]:
        return self._results_manager.get_files()

    def _is_cwl(self, code: Dict):
        return 'cwlVersion' in code.keys()

    def get_pid(self) -> Tuple[int, int]:
        """:return: The process id and his parents id."""
        return self._pid

    def do_complete(self, code: str, cursor_pos: int):
        self.log.debug(f"code: {code}\ncursor_pos: {cursor_pos}\ncode[{cursor_pos}]=XXX")
        suggestions = self._auto_complete_engine.suggest(code, cursor_pos)
        self.log.debug(f'suggestions: {suggestions["matches"]}')
        return {**suggestions, 'status': 'ok'}

    def send_text_to_stdout(self, text: str):
        self.send_response(self.iopub_socket, 'stream', {'name': 'stdout', 'text': text})


if __name__ == '__main__':
    from ipykernel.kernelapp import IPKernelApp

    IPKernelApp.launch_instance(kernel_class=CWLKernel)
