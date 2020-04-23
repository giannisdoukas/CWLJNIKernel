import tempfile
import unittest
from pathlib import Path

from ruamel import yaml
import ruamel

from cwlkernel.CWLBuilder import CWLBuilder


class Test_CWLBuilder(unittest.TestCase):
    maxDiff = None

    def test_build(self):
        cwl_builder = CWLBuilder()

        cell = "\n".join([
            "#!/usr/bin/env cwl-runner",
            "cwlVersion: v1.0",
            "class: CommandLineTool",
            "baseCommand: echo"
        ])
        cwl_builder.append(cell)
        self.assertEqual(
            """#!/usr/bin/env cwl-runner
cwlVersion: v1.0
class: CommandLineTool
baseCommand: echo""",
            cwl_builder.get_current_code()
        )

        cell = "\n".join(["stdout: output.txt", "inputs:"])
        cwl_builder.append(cell)

        self.assertEqual(
            """#!/usr/bin/env cwl-runner
cwlVersion: v1.0
class: CommandLineTool
baseCommand: echo
stdout: output.txt
inputs:""",
            cwl_builder.get_current_code()
        )

        cwl_builder.append("""
message:
  type: string
  inputBinding:
  position: 1""", indent=2)
        self.assertEqual(
            """#!/usr/bin/env cwl-runner
cwlVersion: v1.0
class: CommandLineTool
baseCommand: echo
stdout: output.txt
inputs:
  
  message:
    type: string
    inputBinding:
    position: 1""",
            cwl_builder.get_current_code()
        )

        temp_file = Path(tempfile.mktemp())
        cwl_builder.build(temp_file)
        with temp_file.open() as f:
            created_code = f.read()


        self.assertDictEqual(
            ruamel.yaml.round_trip_load(cwl_builder.get_current_code()),
            ruamel.yaml.round_trip_load(created_code)
        )