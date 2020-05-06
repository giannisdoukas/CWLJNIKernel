import unittest
from copy import deepcopy

from cwlkernel.cwlrepository.cwlrepository import ToolsRepository, MissingIdError
from cwlkernel.cwlrepository.cwltool import Tool


class CWLRepositoryTestCase(unittest.TestCase):
    maxDiff = None

    def test_register_tool(self):
        tool_to_register = Tool({
            "class": "CommandLineTool",
            "label": "Example trivial wrapper for Java 9 compiler",
            "hints": [
                {
                    "dockerPull": "openjdk:9.0.1-11-slim",
                    "class": "DockerRequirement"
                }
            ],
            "baseCommand": "javac",
            "arguments": [
                "-d",
                "$(runtime.outdir)"
            ],
            "inputs": [
                {
                    "type": "File",
                    "inputBinding": {
                        "position": 1
                    },
                    "id": "#arguments.cwl/src"
                }
            ],
            "outputs": [
                {
                    "type": "File",
                    "outputBinding": {
                        "glob": "*.class"
                    },
                    "id": "#arguments.cwl/classfile"
                }
            ],
            "id": "#arguments.cwl"
        })
        repo = ToolsRepository()
        repo.delete()

        repo.register_tool(tool_to_register)

        tools = [tool for tool in ToolsRepository.get_instance()]
        self.assertEqual(1, len(tools))
        self.assertEqual('CommandLineTool', tools[0]['class'])

        tool_without_id = deepcopy(tool_to_register)
        tool_without_id._tool.pop('id')
        with self.assertRaises(MissingIdError):
            repo.register_tool(tool_without_id)

        tool_without_input_id = deepcopy(tool_to_register)
        tool_without_input_id._tool['inputs'][0].pop('id')
        with self.assertRaises(MissingIdError):
            repo.register_tool(tool_without_input_id)

        tool_without_outputs_id = deepcopy(tool_to_register)
        tool_without_outputs_id._tool['outputs'][0].pop('id')
        with self.assertRaises(MissingIdError):
            repo.register_tool(tool_without_outputs_id)

    def test_get_tool(self):
        tools_to_register = [
            {
                "class": "CommandLineTool",
                "label": "Example trivial wrapper for Java 9 compiler",
                "hints": [
                    {
                        "dockerPull": "openjdk:9.0.1-11-slim",
                        "class": "DockerRequirement"
                    }
                ],
                "baseCommand": "javac",
                "arguments": [
                    "-d",
                    "$(runtime.outdir)"
                ],
                "inputs": [
                    {
                        "type": "File",
                        "inputBinding": {
                            "position": 1
                        },
                        "id": "#arguments.cwl/src"
                    }
                ],
                "outputs": [
                    {
                        "type": "File",
                        "outputBinding": {
                            "glob": "*.class"
                        },
                        "id": "#arguments.cwl/classfile"
                    }
                ],
                "id": "#arguments.cwl"
            },
            {
                "class": "CommandLineTool",
                "baseCommand": [
                    "tar",
                    "--extract"
                ],
                "inputs": [
                    {
                        "type": "string",
                        "inputBinding": {
                            "position": 1
                        },
                        "id": "#main/extractfile"
                    },
                    {
                        "type": "File",
                        "inputBinding": {
                            "prefix": "--file"
                        },
                        "id": "#main/tarfile"
                    }
                ],
                "outputs": [
                    {
                        "type": "File",
                        "outputBinding": {
                            "glob": "$(inputs.extractfile)"
                        },
                        "id": "#main/extracted_file"
                    }
                ],
                "id": "#main",
                "cwlVersion": "v1.0"
            }
        ]
        tools_to_register = [Tool(t) for t in tools_to_register]
        repo = ToolsRepository()
        repo.delete()

        with self.assertRaises(TypeError):
            repo.register_tools(tools_to_register)
        repo.register_tools(*tools_to_register)

        tool = repo.get_by_id('#main')
        self.assertDictEqual(tools_to_register[1]._tool, tool._tool)


if __name__ == '__main__':
    unittest.main()
