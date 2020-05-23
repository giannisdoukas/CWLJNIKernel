class: CommandLineTool
cwlVersion: v1.0
id: grep
baseCommand:
  - grep
inputs:
  - id: query
    type: string
    inputBinding:
      position: 0
  - id: lines_bellow
    type: int?
    inputBinding:
      position: 1
      prefix: '-A'
  - id: lines_above
    type: int?
    inputBinding:
      position: 2
      prefix: '-B'
  - id: grepinput
    type: File
    inputBinding:
      position: 10
outputs:
  - id: grepoutput
    type: stdout
label: head
stdout: grepoutput.out