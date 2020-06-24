For Developers
===============

Custom Magic Commands Extensions
------------------------------------------------

The kernel is designed to be able extendable. The methodology for creating extensions is inspired by `IPython's Magic
Commands <https://ipython.readthedocs.io/en/stable/config/custommagics.html>`_. Developers can create new custom magic
commands.

Jupyter Notebook's cells that contain magic commands cannot contain CWL code. The magic command format is the following:
:code:`% [command] [argument_string]`. The argument string is multiline and contains all the content after the
magic command until the end of the cell or the next magic command. For example, at the following snippet, the first time
the argument_string will contain as a single string the string from arg1 until the bar and at the second example, the
argument_string will be an empty string.


.. code-block::

   % command1 arg1 arg2
   foo: bar
   % command2


Kernel's configuration is based on system's environment variables and it is managed by the
:class:`cwlkernel.CWLExecuteConfigurator.CWLExecuteConfigurator`. The CWLKERNEL_MAGIC_COMMANDS_DIRECTORY variable
holds the path that the kernel will search for python scripts to execute them. Check the :ref:`basic_magic_example`.

.. _basic_magic_example:

Basic Example: Custom Magic Command
------------------------------------------------

In the presented example we want to create magic command which prints the message hello world. Firstly, the
directory of the custom magic commands should be configured.

.. code-block:: sh

   mkdir -p ~/.cwlkernel/startup/
   cd ~/.cwlkernel/startup/
   export CWLKERNEL_MAGIC_COMMANDS_DIRECTORY=$(pwd)
   echo $CWLKERNEL_MAGIC_COMMANDS_DIRECTORY

Inside the directory, we create the following file `hello.py`.

.. code-block:: python
   :linenos:
   :emphasize-lines: 3

   from cwlkernel.CWLKernel import CWLKernel

   @CWLKernel.register_magic
   def hello(kernel: CWLKernel, argument_string: str):
       kernel.send_response(
           kernel.iopub_socket,
           'stream',
           {'name': 'stdout', 'text': 'hello world'}
       )


The decorator is required to register the magic command to the kernel. Every magic command should have that signature.
In case that the magic command does not accept any arguments, like in that case the argument string will be just an
empty string. Now, we can open a jupyter notebook and run the following command.

.. code-block::

   % hello

If we want to build a command with more arguments with complicated structure, the usage of
`argparse <https://docs.python.org/3/library/argparse.html>`_ is suggested. For
example the aforementioned example could be changed to:

.. code-block:: python
   :linenos:

   from cwlkernel.CWLKernel import CWLKernel
   import argparse

   @CWLKernel.register_magic
   def hello(kernel: CWLKernel, argument_string: str):
       parser = argparse.ArgumentParser()
       parser.add_argument(
           'messages', nargs='*', type=str, default=['hello world']
       )
       args = parser.parse_args(argument_string.split())
       for message in args.messages:
           kernel.send_response(
               kernel.iopub_socket,
               'stream',
               {'name': 'stdout', 'text': message + '\n'}
           )



Code Details
--------------
.. toctree::
   :maxdepth: 2

   code
