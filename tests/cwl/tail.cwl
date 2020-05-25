class: CommandLineTool
cwlVersion: v1.0
id: tail
baseCommand:
  - tail
inputs:
  - id: number_of_lines
    type: int?
    inputBinding:
      position: 0
      prefix: '-n'
  - id: tailinput
    type: File
    inputBinding:
      position: 1
outputs:
  - id: tailoutput
    type: stdout
label: tail
stdout: tail.out

