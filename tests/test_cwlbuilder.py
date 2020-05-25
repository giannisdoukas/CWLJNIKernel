import tempfile
import unittest
from pathlib import Path

import yaml
from io import StringIO

from cwlkernel.CWLBuilder import CWLSnippetBuilder


class Test_CWLBuilder(unittest.TestCase):
    maxDiff = None

    def test_snippet_builder(self):
        cwl_builder = CWLSnippetBuilder()

        cell = "\n".join([
            "#!/usr/bin/env cwl-runner",
            "cwlVersion: v1.0",
            "id: test",
            "class: CommandLineTool",
            "baseCommand: echo"
        ])
        cwl_builder.append(cell)
        self.assertEqual(
            """#!/usr/bin/env cwl-runner
cwlVersion: v1.0
id: test
class: CommandLineTool
baseCommand: echo""",
            cwl_builder.get_current_code()
        )

        cell = "\n".join(["stdout: output.txt", "inputs:"])
        cwl_builder.append(cell)

        self.assertEqual(
            """#!/usr/bin/env cwl-runner
cwlVersion: v1.0
id: test
class: CommandLineTool
baseCommand: echo
stdout: output.txt
inputs:""",
            cwl_builder.get_current_code()
        )

        cwl_builder.append("""
- id: message
  type: string
  inputBinding:
  position: 1""", indent=2)
        self.assertEqual(
            """#!/usr/bin/env cwl-runner
cwlVersion: v1.0
id: test
class: CommandLineTool
baseCommand: echo
stdout: output.txt
inputs:
  
  - id: message
    type: string
    inputBinding:
    position: 1""",
            cwl_builder.get_current_code()
        )

        cwl_builder.append("""outputs: []""")
        self.assertEqual(
            """#!/usr/bin/env cwl-runner
cwlVersion: v1.0
id: test
class: CommandLineTool
baseCommand: echo
stdout: output.txt
inputs:
  
  - id: message
    type: string
    inputBinding:
    position: 1
outputs: []""",
            cwl_builder.get_current_code()
        )

        cwl_workflow = cwl_builder.build()

        self.assertDictEqual(
            yaml.load(StringIO(cwl_builder.get_current_code()), yaml.Loader),
            yaml.load(StringIO(cwl_workflow.to_yaml()), yaml.Loader)
        )
