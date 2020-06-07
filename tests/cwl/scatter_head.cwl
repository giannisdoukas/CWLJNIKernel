cwlVersion: v1.1
class: Workflow
id: scatter-head
inputs:
  files:
    type: File[]
outputs:
  output_files:
    type: File[]
    outputSource: head/headoutput
steps:
  head:
    run: head.cwl
    scatter: headinput
    in:
      headinput: files
    out:
      - headoutput
requirements:
  ScatterFeatureRequirement: {}
  InlineJavascriptRequirement: {}
