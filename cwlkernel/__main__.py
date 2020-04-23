from ipykernel.kernelapp import IPKernelApp

from .CWLKernel import CWLKernel

IPKernelApp.launch_instance(kernel_class=CWLKernel)
