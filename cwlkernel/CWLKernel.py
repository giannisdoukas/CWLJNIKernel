import os
from typing import List, Dict

from ipykernel.kernelbase import Kernel

from cwlkernel.CWLExecuteConfigurator import CWLExecuteConfigurator
from cwlkernel.IOManager import IOFileManager


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

    def do_execute(self, code: str, silent, store_history: bool=True,
                   user_expressions=None, allow_stdin: bool=False) -> Dict:
        self._yaml_input_data.append(code)

        return {
            'status': 'ok',
            # The base class increments the execution count
            'execution_count': self.execution_count,
            'payload': [],
            'user_expressions': {},
        }

    def get_past_results(self) -> List[str]:
        raise NotImplementedError()

if __name__ == '__main__':
    from ipykernel.kernelapp import IPKernelApp
    IPKernelApp.launch_instance(kernel_class=CWLKernel)
