import unittest
from io import StringIO
import yaml
from cwlkernel.cwlrepository.CWLComponent import WorkflowComponent, CWLTool, CWLWorkflow


class CWLComponentTest(unittest.TestCase):
    maxDiff = None

    def test_simple_composition(self):
        final_workflow = CWLWorkflow(id='one-step')
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
                            "run": "head",
                            "in": {"headinput": "inputfile"},
                            "out": []
                        },
                },
                'requirements': {}
            },
            yaml.load(StringIO(final_workflow.to_yaml()), Loader=yaml.BaseLoader))

    def test_two_connect_io_between_steps(self):
        final_workflow = CWLWorkflow(id='main')
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
                            "run": "head",
                            "in": {"headinput": "inputfile"},
                            "out": ['headoutput']
                        },
                    "tail":
                        {
                            "run": "tail",
                            "in": {"tailinput": "head/headoutput"},
                            "out": []
                        },
                },
                'requirements': {}
            },
            yaml.load(StringIO(final_workflow.to_yaml()), Loader=yaml.BaseLoader))

    def test_two_connect_io_between_steps_nested_yaml(self):
        final_workflow = CWLWorkflow(id='main')
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
                            "run": {'class': 'CommandLineTool',
                                    'id': 'head',
                                    'baseCommand': ['head'],
                                    'inputs': [{'id': 'number_of_lines',
                                                'type': 'int?',
                                                'inputBinding': {'position': 0, 'prefix': '-n'}},
                                               {'id': 'headinput', 'type': 'File',
                                                'inputBinding': {'position': 1}}],
                                    'outputs': [{'id': 'headoutput', 'type': 'stdout'}],
                                    'label': 'head',
                                    'stdout': 'head.out'},
                            "in": {"headinput": "inputfile"},
                            "out": ["headoutput"]
                        },
                    "tail":
                        {
                            "run": {'class': 'CommandLineTool',
                                    'id': 'tail',
                                    'baseCommand': ['tail'],
                                    'inputs': [{'id': 'number_of_lines',
                                                'type': 'int?',
                                                'inputBinding': {'position': 0, 'prefix': '-n'}},
                                               {'id': 'tailinput', 'type': 'File',
                                                'inputBinding': {'position': 1}}],
                                    'outputs': [{'id': 'tailoutput', 'type': 'stdout'}],
                                    'label': 'tail',
                                    'stdout': 'tail.out'},
                            "in": {"tailinput": "head/headoutput"},
                            "out": []
                        },
                },
                'requirements': {}
            },
            yaml.load(StringIO(final_workflow.to_yaml(nested=True)), Loader=yaml.Loader))


if __name__ == '__main__':
    unittest.main()
