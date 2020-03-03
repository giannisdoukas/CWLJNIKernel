#!/usr/bin/env cwl-runner

cwlVersion: v1.0
class: CommandLineTool
baseCommand: [touch, touchedfile.txt]
inputs: {}
outputs:
    example_out:
        type: File
        outputBinding:
            glob: touchedfile.txt
