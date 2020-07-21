import argparse
import json
import os
import random
import subprocess
import traceback
import xml.etree.ElementTree as ET
from collections import OrderedDict
from copy import deepcopy
from io import StringIO
from pathlib import Path
from typing import List, Tuple, Dict, Optional

import pydot
from cwltool.cwlviewer import CWLViewer
from cwltool.main import main as cwltool_main
from ruamel.yaml import YAML

from .CWLKernel import CONF as CWLKernel_CONF
from .CWLKernel import CWLKernel
from .cwlrepository.CWLComponent import CWLWorkflow, WorkflowComponentFactory, WorkflowComponent


@CWLKernel.register_magic('newWorkflowBuild')
def new_workflow_build(kernel: CWLKernel, *args):
    kernel.send_json_response(kernel.workflow_composer.to_dict())
    kernel.workflow_repository.register_tool(kernel.workflow_composer)
    kernel.workflow_composer = None


@CWLKernel.register_magic('newWorkflowAddInput')
def new_workflow_add_input(kernel: CWLKernel, args: str):
    import yaml as y
    args = args.splitlines()
    step_id, step_in_id = args[0].split()
    input_description = '\n'.join(args[1:])
    input_description = y.safe_load(StringIO(input_description))
    kernel.workflow_composer.add_input(
        workflow_input=input_description,
        step_id=step_id.strip(),
        in_step_id=step_in_id.strip())


@CWLKernel.register_magic('newWorkflowAddStepIn')
def new_workflow_add_step_in(kernel: CWLKernel, args: str):
    args = args.splitlines()
    step_in_args = args[0].split()
    input_description = '\n'.join(args[1:])
    import yaml as y
    input_description = y.safe_load(StringIO(input_description))
    for input_id, description in input_description.items():
        kernel.workflow_composer.add_step_in_out(description, input_id, *step_in_args)


@CWLKernel.register_magic('newWorkflowAddStep')
def new_workflow_add_step(kernel: CWLKernel, ids: str):
    tool_id, step_id = ids.split()
    tool = kernel.workflow_repository.get_by_id(tool_id)
    kernel.workflow_composer.add(tool, step_id)


@CWLKernel.register_magic('newWorkflowAddOutputSource')
def new_workflow_add_output_source(kernel: CWLKernel, args: str):
    reference, type_of = args.split()
    kernel.workflow_composer.add_output_source(reference, type_of)


@CWLKernel.register_magic('newWorkflow')
def new_workflow(kernel: CWLKernel, workflow_id: str):
    kernel.workflow_composer = CWLWorkflow(workflow_id)


@CWLKernel.register_magic()
def snippet(kernel: CWLKernel, command: str):
    """
    Submit a cwl workflow incrementally. Usage:
    % snippet add
    [...]
    % snippet add
    [...]
    % snippet build

    @param kernel:
    @param command:
    @return:
    """
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
        kernel.workflow_repository.register_tool(workflow)
        current_code = y.load(StringIO(kernel._snippet_builder.get_current_code()))
        kernel._snippet_builder.clear()
    else:
        raise ValueError()
    kernel.send_json_response(current_code)


class ExecutionMagics:

    @staticmethod
    def _parse_args(execute_argument_string: str):
        execute_argument_string = execute_argument_string.splitlines()
        cwl_id = execute_argument_string[0].strip()
        yaml_str_data = '\n'.join(execute_argument_string[1:])
        return cwl_id, yaml_str_data

    @staticmethod
    def _execute(kernel: CWLKernel, execute_argument_string: str, provenance: bool = False):
        cwl_id, yaml_str_data = ExecutionMagics._parse_args(execute_argument_string)
        cwl_component_path: Path = kernel.workflow_repository.get_tools_path_by_id(cwl_id)
        kernel._set_data(yaml_str_data)
        kernel._execute_workflow(cwl_component_path, cwl_id, provenance=provenance)
        kernel._clear_data()

    @staticmethod
    @CWLKernel.register_magic()
    def execute(kernel: CWLKernel, execute_argument_string: str):
        """
        Execute registered tool by id.
        % execute [tool-id]
        [yaml input ...]

        @param kernel: the kernel instance
        @param execute_argument_string: a multiple line string containins in the first line the tool id and in the next
        lines the input parameters in yaml syntax
        @return: None
        """
        ExecutionMagics._execute(kernel, execute_argument_string, provenance=False)

    @staticmethod
    @CWLKernel.register_magic('executeWithProvenance')
    def execute_with_provenance(kernel: CWLKernel, execute_argument_string: str):
        ExecutionMagics._execute(kernel, execute_argument_string, provenance=True)

    @staticmethod
    @CWLKernel.register_magics_suggester('execute')
    def suggest_execution_id(query_token: str, *args, **kwargs) -> List[str]:
        return [
            command for command in
            CWLKernel.instance()._workflow_repository._registry.keys()
            if command.upper().startswith(query_token.upper())
        ]


@CWLKernel.register_magic('displayData')
def display_data(kernel: CWLKernel, data_name: str) -> None:
    """
    Display the data generated by workflow.
    Usage % displayData [data id]

    @param kernel: the kernel instance
    @param data_name: the data id
    @return None
    """
    if not isinstance(data_name, str) or len(data_name.split()) == 0:
        kernel.send_error_response(
            'ERROR: you must select an output to display. Correct format:\n % displayData [output name]'
        )
        return
    result = kernel.results_manager.get_last_result_by_id(data_name)
    if result is None:
        kernel.send_response(kernel.iopub_socket, 'stream', {'name': 'stderr', 'text': 'Result not found'})
        return
    with open(result) as f:
        data = f.read()
    kernel.send_response(kernel.iopub_socket, 'stream', {'name': 'stdout', 'text': data})


@CWLKernel.register_magic('displayDataCSV')
def display_data_csv(kernel: CWLKernel, data_name: str):
    import pandas as pd
    if not isinstance(data_name, str) or len(data_name.split()) == 0:
        kernel.send_error_response(
            'ERROR: you must select an output to display. Correct format:\n % display_data_csv [output name]'
        )
        return
    result = kernel.results_manager.get_last_result_by_id(data_name)
    if result is None:
        kernel.send_error_response('Result not found')
        return

    df = pd.read_csv(result, header=None)
    kernel.send_response(
        kernel.iopub_socket,
        'display_data',
        {
            'data': {
                "text/html": f"""{df.to_html(index=False)}""",
                "text/plain": f"{str(df)}"
            },
            'metadata': {},
        },
    )


@CWLKernel.register_magic('sampleCSV')
def sample_csv(kernel: CWLKernel, args: str):
    import pandas as pd
    try:
        data_name, sample_percent = args.split()
        sample_percent = float(sample_percent)
    except Exception:
        kernel.send_error_response(
            'ERROR: you must select an output to display. Correct format:\n '
            '% sample_csv [output name] [percent size (0.5)]'
        )
        return
    result = kernel.results_manager.get_last_result_by_id(data_name)
    if result is None:
        kernel.send_error_response('Result not found')
        return

    df = pd.read_csv(result, header=None, skiprows=lambda i: i > 0 and random.random() > sample_percent)
    kernel.send_response(
        kernel.iopub_socket,
        'display_data',
        {
            'data': {
                "text/html": f"""{df.to_html(index=False)}""",
                "text/plain": f"{str(df)}"
            },
            'metadata': {},
        },
    )


@CWLKernel.register_magic('displayDataImage')
def display_data_image(kernel: CWLKernel, data_name: str):
    import base64
    if not isinstance(data_name, str) or len(data_name.split()) == 0:
        kernel.send_error_response(
            'ERROR: you must select an output to display. Correct format:\n % display_data [output name]'
        )
        return
    result = kernel.results_manager.get_last_result_by_id(data_name)
    if result is None:
        kernel.send_error_response('Result not found')
        return

    kernel.log.debug(result)
    with open(result, 'rb') as f:
        image = base64.b64encode(f.read()).decode()
    if result.endswith('.png'):
        mime = 'image/png'
    elif result.endswith('.jpg') or result.endswith('.jpeg'):
        mime = 'image/jpeg'
    elif result.endswith('.svg'):
        mime = 'image/svg+xml'
    else:
        raise ValueError(f'unsupported type {result}')
    image = f"""<image src="data:{mime}; base64, {image}" alt="{result}" style="max-width: 100%">"""
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


@CWLKernel.register_magic()
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
                'text/plain': json.dumps(list(kernel._cwl_logger.load(limit))),
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


@CWLKernel.register_magic()
def data(kernel: CWLKernel, *args):
    """
    Display all the data which are registered in the kernel session.
    """
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


@CWLKernel.register_magic('githubImport')
def github_import(kernel: CWLKernel, url: str):
    cwl_factory = WorkflowComponentFactory()
    for cwl_file in kernel._github_resolver.resolve(url):
        try:
            with open(cwl_file) as f:
                file_data = f.read()
            cwl_component = cwl_factory.get_workflow_component(file_data)
            cwl_component._id = os.path.splitext(os.path.basename(cwl_file))[0]
            relative_dir = Path(os.path.relpath(cwl_file, kernel._github_resolver._local_root_directory.as_posix()))
            kernel.workflow_repository.register_tool(cwl_component, relative_dir)
            kernel.send_response(kernel.iopub_socket, 'stream',
                                 {'name': 'stdout', 'text': f"tool '{cwl_component.id}' registered\n"})
        except Exception as e:
            kernel.send_error_response(f'Error on loading tool "{cwl_file}"\n')
            stacktrace_error = StringIO()
            traceback.print_exc(file=stacktrace_error)
            kernel.send_error_response(f'Error: {e}\n{stacktrace_error.getvalue()}')


@CWLKernel.register_magic('viewTool')
def view_tool(kernel: CWLKernel, workflow_id: str):
    workflow = kernel.workflow_repository.__repo__.get_by_id(workflow_id)
    if workflow is not None:
        kernel.send_json_response(workflow.to_dict())
    else:
        kernel.send_error_response(f"Tool '{workflow_id}' is not registered")


@CWLKernel.register_magic()
def magics(kernel: CWLKernel, arg: str):
    arg = arg.split()
    parser = argparse.ArgumentParser()
    parser.add_argument('magic', default=None, nargs='?')
    arg = parser.parse_args(arg)
    if arg.magic is None:
        commands = ['\t- ' + cmd for cmd in kernel._magic_commands.keys()]
        commands.sort()
        commands = os.linesep.join(commands)
        kernel.send_text_to_stdout(
            f'List of Available Magic commands\n{commands}'
        )
    else:
        try:
            full_doc: str = kernel._magic_commands[arg.magic].__doc__.splitlines()
            doc = []
            for line in full_doc:
                line = line.strip()
                if line.startswith('@'):
                    break
                elif len(line) > 0:
                    doc.append(line)
            doc = os.linesep.join(doc)

            kernel.send_text_to_stdout(doc)
        except Exception:
            kernel.send_text_to_stdout(
                'The function does not provide documentation'
            )


@CWLKernel.register_magic('view')
def visualize_graph(kernel: CWLKernel, tool_id: str):
    """Visualize a Workflow"""
    tool_id = tool_id.strip()
    path = kernel.workflow_repository.get_tools_path_by_id(tool_id)
    rdf_stream = StringIO()
    import logging
    handler = logging.StreamHandler()
    cwltool_main(['--print-rdf', os.path.abspath(path)], stdout=rdf_stream, logger_handler=handler)
    cwl_viewer = CWLViewer(rdf_stream.getvalue())
    (dot_object,) = pydot.graph_from_dot_data(cwl_viewer.dot())
    ET.register_namespace('', 'http://www.w3.org/2000/svg')
    image_xml = ET.fromstring(dot_object.create('dot', 'svg').decode())
    image_container = f'<div style="max-width: 100%;">{ET.tostring(image_xml, method="html").decode()}</div>'
    kernel.send_response(
        kernel.iopub_socket,
        'display_data',
        {
            'data': {
                "text/html": image_container,
                "text/plain": image_container
            },
            'metadata': {},
        },

    )


@CWLKernel.register_magic()
def system(kernel: CWLKernel, commands: str):
    """
    Execute bash commands in the Runtime Directory of the session.

    @param kernel:
    @param commands:
    @return:
    """
    result = subprocess.run(
        commands,
        stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        shell=True, cwd=kernel.runtime_directory.as_posix()
    )
    stdout = result.stdout.decode()
    stderr = result.stderr.decode()
    if len(stdout) > 0:
        kernel.send_text_to_stdout(stdout)
    if len(stderr) > 0:
        kernel.send_error_response(stderr)


class Scatter:
    parser = argparse.ArgumentParser()
    parser.add_argument('tool_id', type=str, nargs=1, )
    parser.add_argument('input_to_scatter', type=str, nargs=1)

    scatter_template = {
        'cwlVersion': None,
        'class': 'Workflow',
        'inputs': None,
        'outputs': None,
        'steps': None,
        'requirements': {'ScatterFeatureRequirement': {}}
    }

    @classmethod
    def parse_args(cls, args_line) -> Tuple[str, str]:
        try:
            args = cls.parser.parse_args(args_line.split())
            return args.tool_id[0], args.input_to_scatter[0]
        except SystemExit:
            raise RuntimeError('wrong arguments on scatter')

    @staticmethod
    @CWLKernel.register_magic()
    def scatter(kernel: CWLKernel, args_line: str):
        tool_id, input_to_scatter = Scatter.parse_args(args_line)
        tool = kernel.workflow_repository.get_instance().get_by_id(tool_id)
        if tool is None:
            kernel.send_error_response(f"Tool '{tool_id}' not found")
            return
        try:
            input_dict = {i['id']: i for i in tool.inputs if input_to_scatter == i['id']}[input_to_scatter]
        except KeyError:
            kernel.send_error_response(f"There is no input '{input_to_scatter}' in tool '{tool_id}'")
            return
        scattered = deepcopy(Scatter.scatter_template)
        scattered['inputs'] = {
            f'{input_dict["id"]}_scatter_array': {
                'type': f'{input_dict["type"]}[]',
            }
        }
        step_name = tool_id

        def output_type(out):
            return out['type'] if out['type'] != 'stdout' and out['type'] != 'stderr' else 'File'

        scattered['outputs'] = {
            f"{out['id']}_scatter_array": {
                'type': f"{output_type(out)}[]",
                'outputSource': f"{step_name}/{out['id']}",
            }
            for out in tool.outputs
        }
        scattered['steps'] = {
            step_name: {
                'run': kernel.workflow_repository.get_instance().get_tools_path_by_id(tool_id).as_posix(),
                'scatter': input_to_scatter,
                'in': {input_to_scatter: f"{input_to_scatter}_scatter_array"},
                'out': [out['id'] for out in tool.outputs],
            }
        }
        scattered['cwlVersion'] = tool.to_dict()['cwlVersion']
        scattered['id'] = f'scattered_{tool_id}'
        workflow = CWLWorkflow(scattered['id'], scattered)
        kernel.workflow_repository.get_instance().register_tool(workflow)
        kernel.send_json_response(scattered)


@CWLKernel.register_magic()
def edit(kernel: CWLKernel, args: str) -> Optional[Dict]:
    args_lines = args.splitlines()
    if len(args_lines) == 0:
        kernel.send_error_response('Missing arguments')
        return
    tool_id = args_lines[0].split()[-1]
    workflow_repo = kernel.workflow_repository.get_instance()
    if len(args_lines) == 1:
        tool = workflow_repo.get_by_id(tool_id)
        if tool is None:
            kernel.send_error_response(f"Tool {tool_id} does not exists")
            return None
        text = os.linesep.join(["% edit " + args_lines[0], tool.to_yaml()])
        return {
            "source": "set_next_input",
            "text": text,
            "replace": True,
        }
    elif len(args_lines) > 1:
        tool_description = os.linesep.join(args_lines[1:])
        workflow_repo.delete_by_id(tool_id)
        workflow_component_factory = WorkflowComponentFactory()
        tool = workflow_component_factory.get_workflow_component(tool_description)
        workflow_repo.register_tool(tool)
        kernel.send_text_to_stdout(f"Tool '{tool_id}' updated")
        kernel.send_json_response(tool.to_dict())


@CWLKernel.register_magic('compile')
def compile_executed_steps_as_workflow(kernel: CWLKernel, args: str):
    """
    Compose a workflow from executed workflows.

    @param kernel:
    @param args:
    @return:
    """
    new_workflow_id = args.strip()
    yml = YAML(typ='rt')
    executions_history = map(
        lambda item: (
            item[1].splitlines()[0].strip(),
            yml.load(StringIO('\n'.join(item[1].splitlines()[1:])))
        ),
        filter(
            lambda h: h[0] == 'magic' and h[1].split()[1] == 'execute',
            kernel.history
        ))
    workflow_composer = CWLWorkflow(new_workflow_id)

    tools_data_tuples = [
        (kernel.workflow_repository.get_instance().get_entry_by_id(command.split()[2]), data)
        for command, data in executions_history
    ]

    outputs: Dict[str, List[Dict]] = {out[0][0].id: out[0][0].outputs for out in tools_data_tuples}
    repository_root_dir = kernel.workflow_repository.get_instance()._file_repository.ROOT_DIRECTORY
    for (tool, tools_full_path), data in tools_data_tuples:  # type: WorkflowComponent, OrderedDict
        workflow_composer.add(tool, tool.id, os.path.relpath(tools_full_path, repository_root_dir))
        for key_id in data:
            if isinstance(data[key_id], dict) and \
                    'class' in data[key_id] and \
                    data[key_id]['class'] == 'File' and \
                    '$data' in data[key_id]:
                step_out, step_out_id = os.path.split(data[key_id]['$data'])
                workflow_composer.add_step_in_out(
                    step_in=tool.id, step_in_name=key_id, connect=data[key_id]['$data'],
                    step_out=step_out, step_out_id=step_out_id
                )
                i = 0
                for i, out in enumerate(outputs[step_out]):
                    if out['id'] == step_out_id:
                        break
                outputs[step_out].pop(i)
            else:
                input_entry = tool.get_input(key_id)
                workflow_composer.add_input(
                    {'id': key_id, 'type': input_entry['type']}, step_id=tool.id, in_step_id=key_id
                )

    def output_type(out):
        return out['type'] if out['type'] != 'stdout' and out['type'] != 'stderr' else 'File'

    for step in outputs:
        for output in outputs[step]:
            output_ref = os.path.join(os.path.join(step, output['id']))
            workflow_composer.add_output_source(output_ref, output_type(output))
    kernel.workflow_repository.get_instance().register_tool(workflow_composer)
    kernel.send_json_response(workflow_composer.to_dict())


# import user's magic commands

if CWLKernel_CONF.CWLKERNEL_MAGIC_COMMANDS_DIRECTORY is not None:
    for magic_file in os.listdir(CWLKernel_CONF.CWLKERNEL_MAGIC_COMMANDS_DIRECTORY):
        magic_file = os.path.abspath(os.path.join(CWLKernel_CONF.CWLKERNEL_MAGIC_COMMANDS_DIRECTORY, magic_file))
        if os.path.isfile(magic_file) and magic_file.endswith('.py'):
            print('external magic command imported', magic_file)
            with open(magic_file) as code:
                # nosec - exec is used
                exec(code.read())  # pylint: disable=exec-used
