class: CommandLineTool
cwlVersion: v1.0
id: tail
baseCommand:
  - tail
inputs:
  - id: tailinput
    type: File
    inputBinding:
      position: 1
outputs:
  - id: tailoutput
    type: stdout
label: tail
stdout: tail.out

