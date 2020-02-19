import os
from typing import List, Dict, Optional

from ipykernel.kernelbase import Kernel
from ruamel.yaml import YAML

from .CWLExecuteConfigurator import CWLExecuteConfigurator
from .CoreExecutor import CoreExecutor
from .IOManager import IOFileManager


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

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        conf = CWLExecuteConfigurator()
        self._yaml_input_data: List[str] = []
        self._results_manager = IOFileManager(os.sep.join([conf.CWLKERNEL_BOOT_DIRECTORY, 'results']))
        runtime_file_manager = IOFileManager(os.sep.join([conf.CWLKERNEL_BOOT_DIRECTORY, 'runtime_data']))
        self._cwl_executor = CoreExecutor(runtime_file_manager)

    def _code_is_valid_yaml(self, code) -> Optional[Dict]:
        yaml = YAML(typ='safe')
        try:
            return yaml.load(code)
        except Exception:
            return None

    def do_execute(self, code: str, silent, store_history: bool = True,
                   user_expressions=None, allow_stdin: bool = False) -> Dict:
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
            self._accumulate_data(code)
        else:
            self._execute_workflow(code)

        return {
            'status': 'ok',
            # The base class increments the execution count
            'execution_count': self.execution_count,
            'payload': [],
            'user_expressions': {},
        }

    def _accumulate_data(self, code):
        self._yaml_input_data.append(code)
        self.send_response(self.iopub_socket, 'stream', {'name': 'stdout', 'text': 'Add data in memory'})

    def _execute_workflow(self, code):
        self._cwl_executor.set_data(self._yaml_input_data)
        self._cwl_executor.set_workflow(code)
        stdout, stderr, exception = self._cwl_executor.execute()
        stdout = stdout.getvalue()
        stderr = stderr.getvalue()
        if len(stdout) > 0:
            self.send_response(self.iopub_socket, 'stream', {'name': 'stdout', 'text': stdout})
        if len(stderr) > 0:
            self.send_response(self.iopub_socket, 'stream', {'name': 'stderr', 'text': stderr})
        if exception is not None:
            self.send_response(self.iopub_socket, 'stream', {'name': 'stderr', 'text': str(exception)})

    def get_past_results(self) -> List[str]:
        raise NotImplementedError()

    def _is_cwl(self, code: Dict):
        return 'cwlVersion' in code.keys()

if __name__ == '__main__':
    from ipykernel.kernelapp import IPKernelApp
    IPKernelApp.launch_instance(kernel_class=CWLKernel)
