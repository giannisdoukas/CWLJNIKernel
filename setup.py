from jupyter_client.kernelspec import KernelSpecManager
from setuptools import setup

name = 'cwlkernel'

setup(
    name=name,
    version='0.1',
    py_modules=['cwlkernel'],
    url='https://github.com/giannisdoukas/CWLJNIKernel',
    author='Yannis Doukas',
    author_email='',
    description='',
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: Apache Software License",
        "Operating System :: OS Independent",
        "Development Status :: 2 - Pre-Alpha"
    ],
)

import sys
import os
kernel_requirements_directory = os.path.join(
    os.path.dirname(os.path.realpath(__file__)),
    'kernelmeta'
)

print('Installing IPython kernel spec')
KernelSpecManager().install_kernel_spec(
    kernel_requirements_directory,
    name,
    user=False,
    prefix=sys.prefix
)