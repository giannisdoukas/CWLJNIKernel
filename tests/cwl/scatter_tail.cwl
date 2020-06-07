cwlVersion: v1.1
class: Workflow
id: scatter-tail
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
