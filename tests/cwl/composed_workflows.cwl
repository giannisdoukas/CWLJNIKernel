cwlVersion: v1.1
class: Workflow
id: scatter-head-tail
inputs:
  files:
    type: File[]
outputs:
  output_files:
    type: File[]
    outputSource: tail/output_files
steps:
  head:
    run: scatter_head.cwl
    in:
      files: files
    out: [output_files]
  tail:
    run: scatter_tail.cwl
    in:
      files: head/output_files
    out: [output_files]
requirements:
  SubworkflowFeatureRequirement: {}