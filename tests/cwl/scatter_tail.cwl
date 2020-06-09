cwlVersion: v1.0
class: Workflow
id: scatter_tail
inputs:
  files:
    type: File[]
outputs:
  output_files:
    type: File[]
    outputSource: tail/tailoutput
steps:
  tail:
    run: tail.cwl
    scatter: tailinput
    in:
      tailinput: files
    out:
      - tailoutput
requirements:
  ScatterFeatureRequirement: {}
  InlineJavascriptRequirement: {}
