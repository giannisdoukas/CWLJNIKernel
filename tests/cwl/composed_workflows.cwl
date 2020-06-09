cwlVersion: v1.0
class: Workflow
id: scatter-head-tail
inputs:
  - id: files
    type: File[]
outputs:
  - id: output_files
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