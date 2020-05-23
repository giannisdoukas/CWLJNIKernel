import unittest
from io import StringIO
import yaml
from cwlkernel.cwlrepository.CWLComponent import WorkflowComponent, CWLTool, CWLWorkflow


class CWLComponentTest(unittest.TestCase):
    maxDiff = None

    def test_composition(self):
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

        # # connect io ...
        # final_workflow.validate()
        #
        # final_workflow.add(grep_tool, extract_input=True)
        # self.assertEqual(2, len(final_workflow.steps))
        # final_workflow.add(tail_tool, extract_output=True)
        # self.assertEqual(3, len(final_workflow.steps))
        # with self.assertRaises(Exception):
        #     final_workflow.validate()


if __name__ == '__main__':
    unittest.main()
