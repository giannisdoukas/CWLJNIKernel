import logging
import os
import tempfile
import unittest
import uuid
from io import StringIO
from pathlib import Path

import yaml

from cwlkernel.CWLExecuteConfigurator import CWLExecuteConfigurator
from cwlkernel.CWLKernel import CWLKernel
from cwlkernel.cwlrepository.CWLComponent import WorkflowComponent, CWLTool, CWLWorkflow, WorkflowComponentFactory
from cwlkernel.cwlrepository.cwlrepository import WorkflowRepository


class CWLComponentTest(unittest.TestCase):
    maxDiff = None

    def setUp(self) -> None:
        CWLKernel.clear_instance()

    @classmethod
    def setUpClass(cls) -> None:
        logging.basicConfig(
            level=logging.DEBUG,
            format='%(asctime)-15s:%(levelname)s:%(name)s:%(process)d:%(message)s'
        )
        cls.data_directory = os.sep.join([os.path.dirname(os.path.realpath(__file__)), '..', 'input_data'])
        cls.cwl_directory = os.sep.join([os.path.dirname(os.path.realpath(__file__)), '..', 'cwl'])
        cls.kernel_root_directory = tempfile.mkdtemp()

    def test_simple_composition(self):
        final_workflow = CWLWorkflow(workflow_id='one-step')
        head_tool: WorkflowComponent = CWLTool('head', {'class': 'CommandLineTool',
                                                        'cwlVersion': 'v1.0',
                                                        'id': 'head',
                                                        'baseCommand': ['head'],
                                                        'inputs': [{'id': 'number_of_lines',
                                                                    'type': 'int?',
                                                                    'inputBinding': {'position': 0, 'prefix': '-n'}},
                                                                   {'id': 'headinput', 'type': 'File',
                                                                    'inputBinding': {'position': 1}}],
                                                        'outputs': [{'id': 'headoutput', 'type': 'stdout'}],
                                                        'label': 'head',
                                                        'stdout': 'head.out'})

        final_workflow.add(head_tool, step_name='head')
        self.assertEqual(1, len(final_workflow.steps))

        final_workflow.add_input({'id': 'inputfile', 'type': 'File'}, step_id='head', in_step_id='headinput')

        self.assertDictEqual(
            {
                "cwlVersion": "v1.0",
                "class": "Workflow",
                "id": "one-step",
                "inputs": [{'id': 'inputfile', 'type': 'File'}],
                "outputs": [],
                "steps": {
                    "head":
                        {
                            "run": "head.cwl",
                            "in": {"headinput": "inputfile"},
                            "out": []
                        },
                },
                'requirements': {}
            },
            yaml.load(StringIO(final_workflow.to_yaml()), Loader=yaml.BaseLoader))

    def test_two_connect_io_between_steps(self):
        final_workflow = CWLWorkflow(workflow_id='main')
        head_tool: WorkflowComponent = CWLTool('head', {'class': 'CommandLineTool',
                                                        'cwlVersion': 'v1.0',
                                                        'id': 'head',
                                                        'baseCommand': ['head'],
                                                        'inputs': [{'id': 'number_of_lines',
                                                                    'type': 'int?',
                                                                    'inputBinding': {'position': 0, 'prefix': '-n'}},
                                                                   {'id': 'headinput', 'type': 'File',
                                                                    'inputBinding': {'position': 1}}],
                                                        'outputs': [{'id': 'headoutput', 'type': 'stdout'}],
                                                        'label': 'head',
                                                        'stdout': 'head.out'})
        tail_tool: WorkflowComponent = CWLTool('tail', {'class': 'CommandLineTool',
                                                        'cwlVersion': 'v1.0',
                                                        'id': 'tail',
                                                        'baseCommand': ['tail'],
                                                        'inputs': [{'id': 'number_of_lines',
                                                                    'type': 'int?',
                                                                    'inputBinding': {'position': 0, 'prefix': '-n'}},
                                                                   {'id': 'tailinput', 'type': 'File',
                                                                    'inputBinding': {'position': 1}}],
                                                        'outputs': [{'id': 'tailoutput', 'type': 'stdout'}],
                                                        'label': 'tail',
                                                        'stdout': 'tail.out'})
        final_workflow.add(head_tool, 'head')
        final_workflow.add_input({'id': 'inputfile', 'type': 'File'}, step_id='head', in_step_id='headinput')
        final_workflow.add(tail_tool, 'tail')
        final_workflow.add_step_in_out(step_in='tail', step_in_name='tailinput', connect='head/headoutput',
                                       step_out='head', step_out_id='headoutput')
        self.assertDictEqual(
            {
                "cwlVersion": "v1.0",
                "class": "Workflow",
                "id": "main",
                "inputs": [{'id': 'inputfile', 'type': 'File'}],
                "outputs": [],
                "steps": {
                    "head":
                        {
                            "run": "head.cwl",
                            "in": {"headinput": "inputfile"},
                            "out": ['headoutput']
                        },
                    "tail":
                        {
                            "run": "tail.cwl",
                            "in": {"tailinput": "head/headoutput"},
                            "out": []
                        },
                },
                'requirements': {}
            },
            yaml.load(StringIO(final_workflow.to_yaml()), Loader=yaml.BaseLoader))

    def test_two_connect_io_between_steps_nested_yaml(self):
        final_workflow = CWLWorkflow(workflow_id='main')
        head_tool: WorkflowComponent = CWLTool('head', {'class': 'CommandLineTool',
                                                        'cwlVersion': 'v1.0',
                                                        'id': 'head',
                                                        'baseCommand': ['head'],
                                                        'inputs': [{'id': 'number_of_lines',
                                                                    'type': 'int?',
                                                                    'inputBinding': {'position': 0, 'prefix': '-n'}},
                                                                   {'id': 'headinput', 'type': 'File',
                                                                    'inputBinding': {'position': 1}}],
                                                        'outputs': [{'id': 'headoutput', 'type': 'stdout'}],
                                                        'label': 'head',
                                                        'stdout': 'head.out'})
        tail_tool: WorkflowComponent = CWLTool('tail', {'class': 'CommandLineTool',
                                                        'cwlVersion': 'v1.0',
                                                        'id': 'tail',
                                                        'baseCommand': ['tail'],
                                                        'inputs': [{'id': 'number_of_lines',
                                                                    'type': 'int?',
                                                                    'inputBinding': {'position': 0, 'prefix': '-n'}},
                                                                   {'id': 'tailinput', 'type': 'File',
                                                                    'inputBinding': {'position': 1}}],
                                                        'outputs': [{'id': 'tailoutput', 'type': 'stdout'}],
                                                        'label': 'tail',
                                                        'stdout': 'tail.out'})
        final_workflow.add(head_tool, 'head')
        final_workflow.add_input({'id': 'inputfile', 'type': 'File'}, step_id='head', in_step_id='headinput')
        final_workflow.add(tail_tool, 'tail')
        final_workflow.add_step_in_out(step_in='tail', step_in_name='tailinput', connect='head/headoutput',
                                       step_out='head', step_out_id='headoutput')
        self.assertDictEqual(
            {
                "cwlVersion": "v1.0",
                "class": "Workflow",
                "id": "main",
                "inputs": [{'id': 'inputfile', 'type': 'File'}],
                "outputs": [],
                "steps": {
                    "head":
                        {
                            "run": 'head.cwl',
                            "in": {"headinput": "inputfile"},
                            "out": ['headoutput']
                        },
                    "tail":
                        {
                            "run": 'tail.cwl',
                            "in": {"tailinput": "head/headoutput"},
                            "out": []
                        },
                },
                'requirements': {}
            },
            yaml.load(StringIO(final_workflow.to_yaml()), Loader=yaml.Loader))

    def test_connect_workflow_with_tool(self):
        workflow_1 = CWLWorkflow(workflow_id='w1')
        head_tool: WorkflowComponent = CWLTool('head', {'class': 'CommandLineTool',
                                                        'cwlVersion': 'v1.0',
                                                        'id': 'head',
                                                        'baseCommand': ['head'],
                                                        'inputs': [{'id': 'number_of_lines',
                                                                    'type': 'int?',
                                                                    'inputBinding': {'position': 0, 'prefix': '-n'}},
                                                                   {'id': 'headinput', 'type': 'File',
                                                                    'inputBinding': {'position': 1}}],
                                                        'outputs': [{'id': 'headoutput', 'type': 'stdout'}],
                                                        'label': 'head',
                                                        'stdout': 'head.out'})
        tail_tool: WorkflowComponent = CWLTool('tail', {'class': 'CommandLineTool',
                                                        'cwlVersion': 'v1.0',
                                                        'id': 'tail',
                                                        'baseCommand': ['tail'],
                                                        'inputs': [{'id': 'number_of_lines',
                                                                    'type': 'int?',
                                                                    'inputBinding': {'position': 0, 'prefix': '-n'}},
                                                                   {'id': 'tailinput', 'type': 'File',
                                                                    'inputBinding': {'position': 1}}],
                                                        'outputs': [{'id': 'tailoutput', 'type': 'stdout'}],
                                                        'label': 'tail',
                                                        'stdout': 'tail.out'})
        workflow_1.add(head_tool, 'head')
        workflow_1.add_input({'id': 'inputfile', 'type': 'File'}, step_id='head', in_step_id='headinput')
        workflow_1.add(tail_tool, 'tail')
        workflow_1.add_step_in_out(step_in='tail', step_in_name='tailinput', connect='head/headoutput',
                                   step_out='head', step_out_id='headoutput')
        self.assertDictEqual(
            {
                "cwlVersion": "v1.0",
                "class": "Workflow",
                "id": "w1",
                "inputs": [{'id': 'inputfile', 'type': 'File'}],
                "outputs": [],
                "steps": {
                    "head":
                        {
                            "run": 'head.cwl',
                            "in": {"headinput": "inputfile"},
                            "out": ['headoutput']
                        },
                    "tail":
                        {
                            "run": 'tail.cwl',
                            "in": {"tailinput": "head/headoutput"},
                            "out": []
                        },
                },
                'requirements': {}
            },
            yaml.load(StringIO(workflow_1.to_yaml()), Loader=yaml.Loader)
        )
        workflow_final = CWLWorkflow(workflow_id="main")
        workflow_final.add(head_tool, 'head')
        workflow_final.add_input({'id': 'inputfile', 'type': 'File'}, step_id='head', in_step_id='headinput')
        workflow_final.add(workflow_1, 'workflow1')
        workflow_final.add_step_in_out(step_in='workflow1', step_in_name='inputfile', connect='head/headoutput',
                                       step_out='head', step_out_id='headoutput')
        self.assertDictEqual(
            {
                "cwlVersion": "v1.0",
                "class": "Workflow",
                "id": "main",
                "inputs": [{'id': 'inputfile', 'type': 'File'}],
                "outputs": [],
                "steps": {
                    "head":
                        {
                            "run": 'head.cwl',
                            "in": {"headinput": "inputfile"},
                            "out": ['headoutput']
                        },
                    "workflow1": {
                        "run": 'w1.cwl',
                        "in": {'inputfile': 'head/headoutput'},
                        "out": [],
                    }
                },
                'requirements': {'SubworkflowFeatureRequirement': {}}
            },
            yaml.load(StringIO(workflow_final.to_yaml()), Loader=yaml.Loader))

    def test_file_repository(self):
        conf = CWLExecuteConfigurator()
        location = os.sep.join([conf.CWLKERNEL_BOOT_DIRECTORY, str(uuid.uuid4()), 'repo'])
        repo = WorkflowRepository(Path(location))
        head_tool: WorkflowComponent = CWLTool(
            'head',
            {
                'class': 'CommandLineTool',
                'cwlVersion': 'v1.0',
                'id': 'head',
                'baseCommand': ['head'],
                'inputs': [{'id': 'number_of_lines',
                            'type': 'int?',
                            'inputBinding': {'position': 0, 'prefix': '-n'}},
                           {'id': 'headinput', 'type': 'File',
                            'inputBinding': {'position': 1}}],
                'outputs': [{'id': 'headoutput', 'type': 'stdout'}],
                'label': 'head',
                'stdout': 'head.out'}
        )
        repo.register_tool(head_tool)
        self.assertEqual(os.path.realpath(repo.get_tools_path_by_id('head').absolute()),
                         os.path.realpath(os.path.join(location, 'head.cwl')))

    def test_connect_workflow_with_workflow(self):
        cwl_factory = WorkflowComponentFactory()
        with open(os.sep.join([self.cwl_directory, 'scatter_head.cwl'])) as f:
            scatter_head: CWLWorkflow = cwl_factory.get_workflow_component(f.read())
        with open(os.sep.join([self.cwl_directory, 'scatter_tail.cwl'])) as f:
            scatter_tail: CWLWorkflow = cwl_factory.get_workflow_component(f.read())
        with open(os.sep.join([self.cwl_directory, 'composed_workflows.cwl'])) as f:
            expected_workflow = yaml.load(StringIO(f.read()), yaml.Loader)
        final_workflow = CWLWorkflow(workflow_id='scatter-head-tail')
        final_workflow.add(scatter_head, 'head')
        final_workflow.add(scatter_tail, 'tail')
        final_workflow.add_input({'id': 'files', 'type': 'File[]'}, 'head', 'files')
        final_workflow.add_step_in_out(
            connect='head/output_files',
            step_in_name='files',
            step_in='tail',
            step_out='head',
            step_out_id='output_files',
        )
        final_workflow.add_output_source('tail/output_files', 'File[]')
        self.assertDictEqual(expected_workflow, final_workflow.to_dict())


if __name__ == '__main__':
    unittest.main()
