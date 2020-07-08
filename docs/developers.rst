For Developers
===============

Custom Magic Commands Extensions
------------------------------------------------

The kernel is designed to be extendable. The methodology for creating extensions is inspired by `IPython's Magic
Commands <https://ipython.readthedocs.io/en/stable/config/custommagics.html>`_. Developers can create new custom magic
commands.

Jupyter Notebook's cells that contain magic commands cannot contain CWL code. The magic command format is the following:
:code:`% [command] [argument_string]`. The argument string is multiline and contains all the content after the
magic command until the end of the cell or the next magic command. For example, at the following snippet, the first time
the argument_string will contain as a single string, the string from arg1 until the bar and at the second example, the
argument_string will be an empty string.


.. code-block::

   % command1 arg1 arg2
   foo: bar
   % command2


Kernel's configuration is based on the system's environment variables and it is managed by the
:class:`cwlkernel.CWLExecuteConfigurator.CWLExecuteConfigurator`. The CWLKERNEL_MAGIC_COMMANDS_DIRECTORY variable
holds the path that the kernel will search for python scripts to execute them. Check the :ref:`basic_magic_example`.

.. _basic_magic_example:

Basic Example: Custom Magic Command
------------------------------------------------

In the presented example we want to create a magic command which prints the message hello world. Firstly, the
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

   @CWLKernel.register_magic()
   def hello(kernel: CWLKernel, argument_string: str):
       kernel.send_response(
           kernel.iopub_socket,
           'stream',
           {'name': 'stdout', 'text': 'hello world'}
       )


The decorator is required to register the magic command to the kernel. Every magic command should have that signature.
In case that the magic command does not accept any arguments, like in this case, the argument string will be just an
empty string. Now, we can open a jupyter notebook and run the following command.

.. code-block::

   % hello

If we want to build command with more arguments with complicated structure, the usage of
`argparse <https://docs.python.org/3/library/argparse.html>`_ is suggested. For
example, the aforementioned example could be changed to:

.. code-block:: python
   :linenos:

   from cwlkernel.CWLKernel import CWLKernel
   import argparse

   @CWLKernel.register_magic()
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


Advanced Example: Custom Magic Command
------------------------------------------------

For custom magic commands with state and complex logic the object-oriented strategy is suggested.
To do that, you have to create a class to encapsulate the logic inside. The state has to be defined as a class attribute.
The method's functionality, which is mapped to magic command, should be defined as a static method and registered as
a magic command with the decorator.


In the following tutorial, we present how to use some of Jupyter's features to build interactive commands.
Jupyter Notebook has a pub-sub communication channel to communicate with the kernel.
There are multiple types of messages that the kernel can send to the notebook.
For more information check `Jupyter's documentation for messaging
<https://jupyter-client.readthedocs.io/en/stable/messaging.html>`_.

In the presented tutorial we will use the `display_data` & `update_display_data` message types to illustrate
how we can build interactive magic commands. Let's suppose that we want to build magic commands to create & visualise
a graph. Also, we want instead of printing the image multiple times to update the initial one.

- add_node: add a new node in the graph
- add_edge: add a new edge in the graph
- bind_view: initialise the graph and bind the image display

To do that we will use the `networkx <https://networkx.github.io/>`_ library and the
`matplotlib <https://matplotlib.org/>`_.

We assume that you have already set up a directory to add custom magic commands, as it is
described in the :ref:`basic_magic_example`. In that directory, lets create a file :code:`interactive.py`.
In order to implement the requirements, we will create a class named BindGraph. The class has a state, the
graph, that we want to visualise, the attribute named G, and a data_id which is required for updating the data
to the notebook.

.. code-block:: python

   class BindGraph:
      G = None
      data_id = '1234'


.. tip:: Technical Recommendation

   The kernel is not aware of the sequence in which the jupyter notebook's cells are, but the kernel receives them in the order that the user executes them. For example, if in the jupyter notebook we have in the following cells
   `% command1` and `% command2`, the user, during his development, may execute them in different/wrong order. For
   use cases in which magic commands have common states, the usage of
   `builder pattern is suggested to be considered
   <https://www.tutorialspoint.com/python_design_patterns/python_design_patterns_builder.htm>`_.

Firstly, we want to create a function for displaying new images or updating existing ones.
To do that, we will use the API provided by jupyter notebook.
In that function, we send from the kernel to the notebook a message including a display_id.
This id is needed to be able to update the image when we request it.
So, we will define the following staticmethod:

.. code-block:: python

   @staticmethod
   def display_image(kernel: CWLKernel, image_html_tag: str, update: bool = False):
      if update:
         message_type = 'update_display_data'
      else:
         message_type = 'display_data'
      kernel.send_response(
         kernel.iopub_socket,
         message_type,
         {
             'data': {
                 "text/html": image_html_tag,
                 "text/plain": f"{image_html_tag}"
             },
             'metadata': {},
             'transient': {
                 'display_id': BindGraph.data_id
             }
         }
      )


Then we want to define the `bind_view` magic command. That command has to initialise
an empty graph and visualise the empty image.

.. code-block:: python

   @staticmethod
   @CWLKernel.register_magic()
   def bind_view(kernel: CWLKernel, arg: str):
      BindGraph.G = nx.Graph()
      image = BindGraph.get_image()
      BindGraph.display_image(kernel, image)


The `get_image` is a staticmethod that we defined to convert the graph to an HTML image tag.

.. code-block:: python

   @staticmethod
   def get_image():
      nx.draw(BindGraph.G, with_labels=True)
      image_stream = BytesIO()
      plt.savefig(image_stream)
      image_base64 = base64.b64encode(image_stream.getvalue()).decode()
      plt.clf()
      mime = 'image/png'
      image = f"""<image src="data:{mime}; base64, {image_base64}" alt="Graph">"""
      return image


The methods for adding node & edge are very similar. For both of the cases, firstly we update
the graph based on the user's argument and then we generate the new image and we send a message for
update. Finally, we also send a message under the cell that the user requested to execute the command
to inform him.

.. code-block:: python

   @staticmethod
   @CWLKernel.register_magic()
   def add_node(kernel: CWLKernel, arg: str):
      BindGraph.G.add_node(arg)
      image = BindGraph.get_image()
      BindGraph.display_image(kernel, image, update=True)
      kernel.send_text_to_stdout('Done!\n')

   @staticmethod
   @CWLKernel.register_magic()
   def add_edge(kernel: CWLKernel, arg: str):
     edges = arg.split()
     BindGraph.G.add_edge(*edges)
     image = BindGraph.get_image()
     BindGraph.display_image(kernel, image, update=True)
     kernel.send_text_to_stdout('Done!\n')


Finally, the full code will look like that:

.. code-block:: python

   import base64
   import networkx as nx
   import matplotlib.pyplot as plt
   from cwlkernel.CWLKernel import CWLKernel
   from io import BytesIO


   class BindGraph:
       G = None
       data_id = '1234'

       @staticmethod
       def display_image(kernel: CWLKernel, image_html_tag: str, update: bool = False):
           if update:
               message_type = 'update_display_data'
           else:
               message_type = 'display_data'
           kernel.send_response(
               kernel.iopub_socket,
               message_type,
               {
                   'data': {
                       "text/html": image_html_tag,
                       "text/plain": f"{image_html_tag}"
                   },
                   'metadata': {},
                   'transient': {
                       'display_id': BindGraph.data_id
                   }
               }
           )

       @staticmethod
       @CWLKernel.register_magic()
       def add_node(kernel: CWLKernel, arg: str):
           BindGraph.G.add_node(arg)
           image = BindGraph.get_image()
           BindGraph.display_image(kernel, image, update=True)
           kernel.send_text_to_stdout('Done!\n')

       @staticmethod
       @CWLKernel.register_magic()
       def add_edge(kernel: CWLKernel, arg: str):
           edges = arg.split()
           BindGraph.G.add_edge(*edges)
           image = BindGraph.get_image()
           BindGraph.display_image(kernel, image, update=True)
           kernel.send_text_to_stdout('Done!\n')

       @staticmethod
       def get_image():
           nx.draw(BindGraph.G, with_labels=True)
           image_stream = BytesIO()
           plt.savefig(image_stream)
           image_base64 = base64.b64encode(image_stream.getvalue()).decode()
           plt.clf()
           mime = 'image/png'
           image = f"""<image src="data:{mime}; base64, {image_base64}" alt="Graph">"""
           return image

       @staticmethod
       @CWLKernel.register_magic()
       def bind_view(kernel: CWLKernel, arg: str):
           BindGraph.G = nx.Graph()
           image = BindGraph.get_image()
           BindGraph.display_image(kernel, image)

       @staticmethod
       def display_image(kernel: CWLKernel, image_html_tag: str, update: bool = False):
           if update:
               message_type = 'update_display_data'
           else:
               message_type = 'display_data'
           kernel.send_response(
               kernel.iopub_socket,
               message_type,
               {
                   'data': {
                       "text/html": image_html_tag,
                       "text/plain": f"{image_html_tag}"
                   },
                   'metadata': {},
                   'transient': {
                       'display_id': BindGraph.data_id
                   }
               }
           )


Code Details
--------------
.. toctree::
   :maxdepth: 2

   code
