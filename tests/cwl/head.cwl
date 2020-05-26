class: CommandLineTool
cwlVersion: v1.0
id: head
baseCommand:
  - head
inputs:
  - id: number_of_lines
    type: int?
    inputBinding:
      position: 0
      prefix: '-n'
  - id: headinput
    type: File
    inputBinding:
      position: 1
outputs:
  - id: headoutput
    type: stdout
label: head
stdout: head.out
