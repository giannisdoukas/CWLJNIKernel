import codecs
import os.path

from setuptools import setup
import glob

name = 'cwlkernel'


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

DATA_FILES = [
    (f'share/jupyter/kernels/{name}', [
        '%s/kernelmeta/kernel.json' % name
    ] + glob.glob('%s/kernelmeta/*.png' % name)
     )
]

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
    data_files=DATA_FILES,
)
