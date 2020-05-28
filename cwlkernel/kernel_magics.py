from io import StringIO

from ruamel.yaml import YAML

from cwlkernel.cwlrepository.CWLComponent import CWLWorkflow, WorkflowComponent
from .CWLKernel import CWLKernel


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
    cwl_component: WorkflowComponent = kernel._workflow_repository.get_by_id(cwl_id)
    kernel._set_data('\n'.join(execute_argument_string[1:]))
    kernel._execute_workflow(cwl_component.to_yaml(True))
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
