import codecs
import os.path

from jupyter_client.kernelspec import KernelSpecManager
from setuptools import setup
from setuptools.command.develop import develop
from setuptools.command.install import install

name = 'cwlkernel'


def install_kernel_specs():
    import sys
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


class PostDevelopCommand(develop):
    """Post-installation for development mode."""

    def run(self):
        develop.run(self)
        install_kernel_specs()


class PostInstallCommand(install):
    """Post-installation for installation mode."""

    def run(self):
        install.run(self)
        install_kernel_specs()


def read(rel_path):
    here = os.path.abspath(os.path.dirname(__file__))
    with codecs.open(os.path.join(here, rel_path), 'r') as fp:
        return fp.read()


def get_version(rel_path):
    for line in read(rel_path).splitlines():
        if line.startswith('__version__'):
            delim = '"' if '"' in line else "'"
            return line.split(delim)[1]
    else:
        raise RuntimeError("Unable to find version string.")


with open(os.sep.join([os.path.abspath(os.path.dirname(__file__)), "README.md"]), "r") as fh:
    long_description = fh.read()

setup(
    name=name,
    version=get_version(f"{name}/__init__.py"),
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
    ],
    cmdclass={
        'develop': PostDevelopCommand,
        'install': PostInstallCommand,
    },
)
