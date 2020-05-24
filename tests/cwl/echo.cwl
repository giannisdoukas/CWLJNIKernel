#!/usr/bin/env cwl-runner

cwlVersion: v1.0
id: echo
class: CommandLineTool
baseCommand: echo
inputs:
- id: message
  inputBinding:
    position: 1
  type: string
outputs: []