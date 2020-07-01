CWLKernel!
=====================================

.. image:: https://travis-ci.com/giannisdoukas/CWLJNIKernel.svg?branch=master
    :target: https://travis-ci.com/giannisdoukas/CWLJNIKernel
.. image:: https://coveralls.io/repos/github/giannisdoukas/CWLJNIKernel/badge.svg?branch=master
    :target: https://coveralls.io/github/giannisdoukas/CWLJNIKernel?branch=master

------------------------------------------------------------

CWLKernel is an Kernel for Jupyter Notebook to enable users to execute `CWL <https://www.commonwl.org/>`_.

---------------------------------------------------------------------------

.. code-block:: yaml

   cwlVersion: v1.1
   class: CommandLineTool
   baseCommand: echo
   inputs:
      message:
      type: string
      inputBinding:
         position: 1
   outputs:
      example_output:
      type: stdout

.. code-block::

   % execute echo
   message: Hello world!

.. code-block:: json

   {
     "basename": "f811c63eed22dec4eec6f02280820eabf16fa779",
     "checksum": "sha1$47a013e660d408619d894b20806b1d5086aab03b",
     "class": "File",
     "http://commonwl.org/cwltool#generation": 0,
     "id": "example_output",
     "location": "file':///private/tmp/CWLKERNEL_DATA/runtime_data/f811c63eed22dec4eec6f02280820eabf16fa779",
     "nameext": "",
     "nameroot": "f811c63eed22dec4eec6f02280820eabf16fa779",
     "size": 13
   }


Installation
---------------------------------------------------------------------------

To install the kernel, download it from `github <https://github.com/giannisdoukas/CWLJNIKernel/releases>`_
and run the python setup.py install.


Contents
------------------------------------------------------------

.. toctree::
   :maxdepth: 3

   users
   developers


Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`

