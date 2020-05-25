#!/usr/bin/env cwltool
cwlVersion: v1.0
class: Workflow
id: threesteps
inputs:
  - id: inputfile
    type: File
  - id: query
    type: string
outputs:
  outputfile:
    type: File
    outputSource: grep2/grepoutput
  outputfile2:
    type: File
    outputSource: grepstep/grepoutput

steps:
  head:
    run: head.cwl
    in:
      headinput: inputfile
    out: [headoutput]

  grepstep:
    run: grep.cwl
    in:
      grepinput: head/headoutput
      query: threesteps/query
      lines_bellow:
        valueFrom: ${return 5;}
    out: [grepoutput]
  grep2:
    run: grep.cwl
    in:
      grepinput: grepstep/grepoutput
      query:
        valueFrom: 'query'
      lines_above:
        valueFrom: ${return 5;}
    out: [grepoutput]
requirements:
  StepInputExpressionRequirement: {}
  InlineJavascriptRequirement: {}
