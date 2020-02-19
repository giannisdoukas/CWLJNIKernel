from typing import List

from ipykernel.kernelbase import Kernel

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
        self._yaml_input_data: List[str] = []

    def do_execute(self, code, silent, store_history=True,
                   user_expressions=None, allow_stdin=False):
        self._yaml_input_data.append(code)

if __name__ == '__main__':
    from ipykernel.kernelapp import IPKernelApp
    IPKernelApp.launch_instance(kernel_class=CWLKernel)
