import json
import logging
import os
import re
import shutil
import traceback
from copy import deepcopy
from io import StringIO
from pathlib import Path
from typing import List, Dict, Optional, Tuple, Union, Callable, NoReturn

from cwltool.provenance import ResearchObject
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

version = "0.0.3"
BOOT_DIRECTORY = Path(os.getcwd()).absolute()
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
    _auto_complete_engine = AutoCompleteEngine(_magic_commands.keys())

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._session_dir = os.path.join(CONF.CWLKERNEL_BOOT_DIRECTORY, self.ident)
        self._boot_directory: Path = BOOT_DIRECTORY
        self._yaml_input_data: Optional[str] = None
        self._results_manager = ResultsManager(os.path.join(self._session_dir, 'results'))
        runtime_file_manager = IOFileManager(os.path.join(self._session_dir, 'runtime_data'))
        self._cwl_executor = CoreExecutor(runtime_file_manager, self._boot_directory)
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
        if self.log is None:  # pylint: disable=access-member-before-definition
            self.log = logging.getLogger()
        self._history: List[Tuple[str, str]] = []

    @property
    def runtime_directory(self) -> Path:
        return Path(self._cwl_executor.file_manager.ROOT_DIRECTORY).absolute()

    @property
    def workflow_repository(self) -> WorkflowRepository:
        return self._workflow_repository

    @property
    def results_manager(self) -> ResultsManager:
        return self._results_manager

    @property
    def workflow_composer(self) -> CWLWorkflow:
        return self._workflow_composer

    @property
    def history(self) -> List[Tuple[str, str]]:
        """Returns a list of executed cells in the current session.
        The first item has the value "magic"/"register" and the second the code """
        return deepcopy(self._history)

    @workflow_composer.setter
    def workflow_composer(self, composer=Optional[CWLWorkflow]):
        self._workflow_composer = composer

    class register_magic:
        """Registers magic commands. That method should be used as a decorator to register custom magic commands."""

        def __init__(self, magics_name: Optional[str] = None):
            self._magics_name = magics_name

        def __call__(self, magic: Callable):
            magics_name = self._magics_name if self._magics_name is not None else magic.__name__
            CWLKernel._magic_commands[magics_name] = magic
            CWLKernel._auto_complete_engine.add_magic_command(magics_name)
            return magic

    class register_magics_suggester:
        """Decorator for registering functions for suggesting commands line arguments"""

        def __init__(self, magic_command_name: str):
            self._magic_command_name = magic_command_name

        def __call__(self, suggester):
            CWLKernel._auto_complete_engine.add_magic_commands_suggester(self._magic_command_name, suggester)
            return suggester

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
        payloads = []
        try:
            if self._is_magic_command(code):
                payloads = self._do_execute_magic_command(code)
                self._history.append(('magic', code))
            else:
                dict_code = self._code_is_valid_yaml(code)
                if dict_code is None:
                    raise RuntimeError('Input cannot be parsed')
                else:
                    self._do_execute_yaml(dict_code, code)
                    self._history.append(('register', code))
        except Exception as e:
            status = 'error'
            traceback.print_exc()
            self.send_error_response(f'{type(e).__name__}: {e}')
        finally:
            # TODO: Payloads are considered deprecated, though their replacement is not yet implemented.
            # https://jupyter-client.readthedocs.io/en/stable/messaging.html#payloads-deprecated
            return {
                'status': status,
                # The base class increments the execution count
                'execution_count': self.execution_count,
                'payload': payloads,
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

    def _do_execute_magic_command(self, commands: str) -> List[Dict]:
        payloads = []
        for command in re.compile(r'^%[ ]+', re.MULTILINE).split(commands):
            command = command.strip()
            if command == '':
                continue
            command = command.split(" ")
            command_name = command[0].strip()
            args = " ".join(command[1:])
            payload = self._magic_commands[command_name](self, args)
            if payload is not None:
                payloads.append(payload)
        return payloads

    def send_error_response(self, text) -> None:
        """
        Sends a response to the jupyter notebook's stderr.
        @param text: The message to display
        @return: None
        """
        self.send_response(self.iopub_socket, 'stream', {'name': 'stderr', 'text': text})

    def send_json_response(self, json_data: Union[Dict, List]) -> None:
        """
        Display a Dict or a List object as a JSON. The object must be json dumpable to use that function.
        @param json_data: Data to print in Jupyter Notebook
        @return: None
        """
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
                if os.path.split(data[key_id]["$data"])[0].strip() == '':
                    raise ValueError("Missing tool id: [tool_id]/[input_id]")
                data[key_id]['location'] = self._results_manager.get_last_result_by_id(data[key_id]["$data"])
                data[key_id].pop('$data')
        if has_change is True:
            self.send_text_to_stdout('set data to:\n')
            self.send_json_response(data)
        return data

    def _clear_data(self):
        self._yaml_input_data = None

    def _execute_workflow(self, code_path: Path, tool_id: str, provenance: bool = False) -> Optional[Exception]:
        input_data = [self._yaml_input_data] if self._yaml_input_data is not None else []
        self._cwl_executor.set_data(input_data)
        self._cwl_executor.set_workflow_path(str(code_path))
        self.log.debug('starting executing workflow ...')
        run_id, results, exception, research_object = self._cwl_executor.execute(provenance)
        for result in results:
            if isinstance(results[result], list):
                for res in results[result]:
                    res['_produced_by'] = tool_id
            else:
                results[result]['_produced_by'] = tool_id
        self.log.debug(f'\texecution results: {run_id}, {results}, {exception}')
        output_directory_for_that_run = str(run_id)
        self.__store_results__(output_directory_for_that_run, results, research_object)
        self.send_json_response(results)
        if exception is not None:
            self.log.debug(f'execution error: {exception}')
            self.send_response(self.iopub_socket, 'stream', {'name': 'stderr', 'text': str(exception)})
        return exception

    def __store_results__(self, output_directory_for_that_run: str, results: Dict,
                          research_object: Optional[ResearchObject]):
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
        if research_object is not None:
            self.send_text_to_stdout(f'\nProvenance stored in directory {research_object.folder}')
            for path, _, files in os.walk(research_object.folder):
                for name in files:
                    file = os.path.relpath(os.path.join(path, name), self._boot_directory.as_posix())
                    self.send_response(
                        self.iopub_socket,
                        'display_data',
                        {
                            'data': {
                                "text/html": f'<a href="/files/{file}">{file}</a>',
                                "text/plain": f"{file}"
                            },
                            'metadata': {},
                        },
                    )

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

    def __del__(self):
        shutil.rmtree(self._session_dir, ignore_errors=True)


if __name__ == '__main__':
    from ipykernel.kernelapp import IPKernelApp

    IPKernelApp.launch_instance(kernel_class=CWLKernel)
