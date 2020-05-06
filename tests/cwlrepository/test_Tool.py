import os
import unittest

from cwlkernel.cwlrepository.cwltool import Tool


class ToolTestCase(unittest.TestCase):
    maxDiff = None

    @classmethod
    def setUpClass(cls) -> None:
        cls.cwl_directory = os.sep.join([os.path.dirname(os.path.realpath(__file__)), '..', 'cwl'])

    def get_cwl_text(self, cwl):
        with open(os.sep.join([self.cwl_directory, cwl])) as f:
            return f.read()

    def test_build_tool_from_yaml_str(self):
        cwl_yaml = self.get_cwl_text('echo.cwl')
        tool = Tool.from_yaml(cwl_yaml)
        self.assertIsInstance(tool, Tool)
        self.assertIsInstance(tool['inputs'], list)

    def test_compose_pending_ports(self):
        tool1 = Tool({
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
        tool2 = Tool({
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
                    "id": "#tar-param.cwl/extractfile"
                },
                {
                    "type": "File",
                    "inputBinding": {
                        "prefix": "--file"
                    },
                    "id": "#tar-param.cwl/tarfile"
                }
            ],
            "outputs": [
                {
                    "type": "File",
                    "outputBinding": {
                        "glob": "$(inputs.extractfile)"
                    },
                    "id": "#tar-param.cwl/extracted_file"
                }
            ],
            "id": "#tar-param.cwl"
        })
        expected_tool = {
            "class": "Workflow",
            "inputs": [
                {
                    "type": "string",
                    "id": "#main/name_of_file_to_extract"
                },
                {
                    "type": "File",
                    "id": "#main/tarball"
                }
            ],
            "outputs": [
                {
                    "type": "File",
                    "outputSource": "#main/compile/classfile",
                    "id": "#main/compiled_class"
                }
            ],
            "steps": [
                {
                    "run": "#arguments.cwl",
                    "in": [
                        {
                            "source": "#main/untar/extracted_file",
                            "id": "#main/compile/src"
                        }
                    ],
                    "out": [
                        "#main/compile/classfile"
                    ],
                    "id": "#main/compile"
                },
                {
                    "run": "#tar-param.cwl",
                    "in": [
                        {
                            "source": "#main/name_of_file_to_extract",
                            "id": "#main/untar/extractfile"
                        },
                        {
                            "source": "#main/tarball",
                            "id": "#main/untar/tarfile"
                        }
                    ],
                    "out": [
                        "#main/untar/extracted_file"
                    ],
                    "id": "#main/untar"
                }
            ],
            "id": "#main"
        }

        tool_composer = tool1.start_composing('#new_id', tool2)
        self.assertDictEqual(
            {
                "#arguments.cwl": {
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
                },
                "#tar-param.cwl": {
                    "inputs": [
                        {
                            "type": "string",
                            "inputBinding": {
                                "position": 1
                            },
                            "id": "#tar-param.cwl/extractfile"
                        },
                        {
                            "type": "File",
                            "inputBinding": {
                                "prefix": "--file"
                            },
                            "id": "#tar-param.cwl/tarfile"
                        }
                    ],
                    "outputs": [
                        {
                            "type": "File",
                            "outputBinding": {
                                "glob": "$(inputs.extractfile)"
                            },
                            "id": "#tar-param.cwl/extracted_file"
                        }
                    ],
                },
                "#new_id": {
                    "inputs": {},
                    "outputs": {},
                }
            },
            tool_composer.pending_ports()
        )

        tool_composer.connect_port()
