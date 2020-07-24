import codecs
import os.path

from setuptools import setup
from setuptools.command.develop import develop
from setuptools.command.install import install

name = 'cwlkernel'


def install_kernel_specs():
    import sys
    try:
        from jupyter_client.kernelspec import KernelSpecManager
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
    except ImportError:
        print('Jupyter is not installed', file=sys.stderr)


class PostDevelopCommand(develop):
    """Post-installation for development mode."""

    def run(self):
        super().run()
        install_kernel_specs()


class PostInstallCommand(install):
    """Post-installation for installation mode."""

    def run(self):
        super().run()
        install_kernel_specs()


def read(rel_path):
    here = os.path.abspath(os.path.dirname(__file__))
    with codecs.open(os.path.join(here, rel_path), 'r') as fp:
        return fp.read()


def get_version(rel_path):
    for line in read(rel_path).splitlines():
        if line.startswith('version'):
            delim = '"' if '"' in line else "'"
            return line.split(delim)[1]
    else:
        raise RuntimeError("Unable to find version string.")


with open(os.sep.join([os.path.abspath(os.path.dirname(__file__)), "README.md"]), "r") as fh:
    long_description = fh.read()

setup(
    name=name,
    version=get_version(f"{name}/CWLKernel.py"),
    packages=['cwlkernel', 'cwlkernel.cwlrepository', 'cwlkernel.git'],
    url='https://github.com/giannisdoukas/CWLJNIKernel',
    author='Yannis Doukas',
    author_email='giannisdoukas2311@gmail.com',
    description='CWL Jupyter Notebook Kernel',
    long_description=long_description,
    long_description_content_type="text/markdown",
    python_requires='>=3.6',
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: Apache Software License",
        "Operating System :: MacOS",
        "Operating System :: POSIX",
        "Development Status :: 2 - Pre-Alpha",
        "Framework :: IPython",
        "Programming Language :: Python :: 3.6",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
    ],
    install_requires=[
        "cwltool>=3.0.20200720165847",
        "jsonschema>=3.2.0",
        "jupyter-client>=5.3.4",
        "jupyter-core>=4.6.3",
        "psutil>=5.7.0",
        "ruamel.yaml<=0.16.5,>=0.12.4",
        "PyYAML>=5.3.1",
        "pandas>=1.0.4",
        "notebook>=6.0.3",
        "requests>=2.23.0",
        "pygtrie>=2.3.3",
        "pydot>=1.4.1",
    ],
    cmdclass={
        'develop': PostDevelopCommand,
        'install': PostInstallCommand,
    },
)
