cwlVersion: v1.0
class: CommandLineTool

baseCommand: ["python"]

inputs:
  script:
    type: File
    inputBinding:
      position: 1
outputs:
  image:
    type: File
    outputBinding:
      glob: test.png
