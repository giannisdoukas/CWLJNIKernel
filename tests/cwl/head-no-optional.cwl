class: CommandLineTool
cwlVersion: v1.0
id: head
baseCommand:
  - head
inputs:
  - id: headinput
    type: File
    inputBinding:
      position: 1
outputs:
  - id: headoutput
    type: stdout
label: head
stdout: head.out
