from io import StringIO

from ruamel.yaml import YAML

from .CWLKernel import CWLKernel
from .cwlrepository.CWLComponent import CWLWorkflow, WorkflowComponent, WorkflowComponentFactory


@CWLKernel.register_magic
def newWorkflowBuild(kernel: CWLKernel, *args):
    kernel._send_json_response(kernel._workflow_composer.to_dict())
    kernel._workflow_repository.register_tool(kernel._workflow_composer)
    kernel._workflow_composer = None


@CWLKernel.register_magic
def newWorkflowAddInput(kernel: CWLKernel, args: str):
    import yaml as y
    args = args.splitlines()
    step_id, step_in_id = args[0].split()
    input_description = '\n'.join(args[1:])
    input_description = y.load(StringIO(input_description), y.Loader)
    kernel._workflow_composer.add_input(
        workflow_input=input_description,
        step_id=step_id.strip(),
        in_step_id=step_in_id.strip())


@CWLKernel.register_magic
def newWorkflowAddStepIn(kernel: CWLKernel, args: str):
    args = args.splitlines()
    step_in_args = args[0].split()
    input_description = '\n'.join(args[1:])
    import yaml as y
    input_description = y.load(StringIO(input_description), y.Loader)
    for input_id, description in input_description.items():
        kernel._workflow_composer.add_step_in_out(description, input_id, *step_in_args)


@CWLKernel.register_magic
def newWorkflowAddStep(kernel: CWLKernel, ids: str):
    tool_id, step_id = ids.split()
    tool = kernel._workflow_repository.get_by_id(tool_id)
    kernel._workflow_composer.add(tool, step_id)


@CWLKernel.register_magic
def newWorkflow(kernel: CWLKernel, id: str):
    kernel._workflow_composer = CWLWorkflow(id)


@CWLKernel.register_magic
def snippet(kernel: CWLKernel, command: str):
    command = command.splitlines()
    command[0] = command[0].strip()
    y = YAML(typ='rt')
    if command[0] == "add":
        snippet = '\n'.join(command[1:])
        kernel._snippet_builder.append(snippet)
        current_code = y.load(StringIO(kernel._snippet_builder.get_current_code()))
    elif command[0] == "build":
        snippet = '\n'.join(command[1:])
        kernel._snippet_builder.append(snippet)
        workflow = kernel._snippet_builder.build()
        kernel._workflow_repository.register_tool(workflow)
        current_code = y.load(StringIO(kernel._snippet_builder.get_current_code()))
        kernel._snippet_builder.clear()
    else:
        raise ValueError()
    kernel._send_json_response(current_code)


@CWLKernel.register_magic
def execute(kernel: CWLKernel, execute_argument_string: str):
    execute_argument_string = execute_argument_string.splitlines()
    cwl_id = execute_argument_string[0].strip()
    cwl_component_path: WorkflowComponent = kernel._workflow_repository.get_tools_path_by_id(cwl_id)
    kernel._set_data('\n'.join(execute_argument_string[1:]))
    kernel._execute_workflow(cwl_component_path)
    kernel._clear_data()


@CWLKernel.register_magic
def display_data(kernel: CWLKernel, data_name: str):
    if not isinstance(data_name, str) or len(data_name.split()) == 0:
        kernel._send_error_response(
            'ERROR: you must select an output to display. Correct format:\n % display_data [output name]'
        )
        return
    results = list(
        filter(lambda item: item[1]['id'] == data_name, kernel._results_manager.get_files_registry().items()))
    if len(results) != 1:
        kernel.send_response(kernel.iopub_socket, 'stream', {'name': 'stderr', 'text': 'Result not found'})
        return
    results = results[0]
    with open(results[0]) as f:
        data = f.read()
    kernel.send_response(kernel.iopub_socket, 'stream', {'name': 'stdout', 'text': data})


@CWLKernel.register_magic
def display_data_csv(kernel: CWLKernel, data_name):
    import pandas as pd
    if not isinstance(data_name, str) or len(data_name.split()) == 0:
        kernel._send_error_response(
            'ERROR: you must select an output to display. Correct format:\n % display_data [output name]'
        )
        return
    results = list(
        filter(lambda item: item[1]['id'] == data_name, kernel._results_manager.get_files_registry().items()))
    if len(results) != 1:
        kernel._send_error_response('Result not found')
        return

    results = results[0]
    df = pd.read_csv(results[0])
    kernel.send_response(
        kernel.iopub_socket,
        'display_data',
        {
            'data': {
                "text/html": f"""{df.to_html()}""",
                "text/plain": f"{str(df)}"
            },
            'metadata': {},
        },

    )


@CWLKernel.register_magic
def display_data_image(kernel: CWLKernel, data_name):
    import base64
    if not isinstance(data_name, str) or len(data_name.split()) == 0:
        kernel._send_error_response(
            'ERROR: you must select an output to display. Correct format:\n % display_data [output name]'
        )
        return
    results = list(
        filter(lambda item: item[1]['id'] == data_name, kernel._results_manager.get_files_registry().items()))
    if len(results) != 1:
        kernel._send_error_response('Result not found')
        return

    results = results[0]
    kernel.log.debug(results)
    with open(results[0], 'rb') as f:
        image = base64.b64encode(f.read()).decode()
    if results[0].endswith('.png'):
        mime = 'image/png'
    elif results[0].endswith('.jpg') or results[0].endswith('.jpeg'):
        mime = 'image/jpeg'
    elif results[0].endswith('.svg'):
        mime = 'image/svg+xml'
    else:
        raise ValueError(f'unsupported type {results[0]}')
    image = f"""<image src="data:{mime}; base64, {image}" alt="{results[0]}">"""
    kernel.send_response(
        kernel.iopub_socket,
        'display_data',
        {
            'data': {
                "text/html": image,
                "text/plain": f"{image}"
            },
            'metadata': {},
        },

    )


@CWLKernel.register_magic
def logs(kernel: CWLKernel, limit=None):
    limit_len = len(limit)
    if limit_len == 0:
        limit = None
    if limit_len > 0:
        limit = limit[0]
    if isinstance(limit, str):
        limit = int(limit)
    kernel.send_response(
        kernel.iopub_socket,
        'display_data',
        {
            'data': {
                'text/plain': '<IPython.core.display.JSON object>',
                'application/json': list(kernel._cwl_logger.load(limit))
            },
            'metadata': {
                'application/json': {
                    'expanded': False,
                    'root': 'root'
                }
            }
        }
    )


@CWLKernel.register_magic
def data(kernel: CWLKernel, *args):
    data = "<ul>\n" + '\n'.join(
        [f'\t<li><a href="file://{d}" target="_empty">{d}</a></li>' for d in kernel.get_past_results()]) + "\n</ul>"
    kernel.send_response(
        kernel.iopub_socket,
        'display_data',
        {
            'data': {
                'text/html': data
            },
            'metadata': {
                'application/json': {
                    'expanded': False,
                    'root': 'root'
                }
            }
        }
    )


@CWLKernel.register_magic
def githubImport(kernel: CWLKernel, url: str):
    cwl_factory = WorkflowComponentFactory()
    for cwl_file in kernel._github_resolver.resolve(url):
        with open(cwl_file) as f:
            file_data = f.read()
        cwl_component = cwl_factory.get_workflow_component(file_data)
        kernel._workflow_repository.register_tool(cwl_component)
        kernel.send_response(kernel.iopub_socket, 'stream',
                             {'name': 'stdout', 'text': f"tool '{cwl_component.id}' registered\n"})


@CWLKernel.register_magic
def viewTool(kernel: CWLKernel, workflow_id: str):
    workflow = kernel._workflow_repository.__repo__.get_by_id(workflow_id)
    if workflow is not None:
        kernel._send_json_response(workflow.to_dict())
    else:
        kernel._send_error_response(f"Tool '{workflow_id}' is not registered")
