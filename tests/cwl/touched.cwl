#!/usr/bin/env cwl-runner

cwlVersion: v1.0
class: CommandLineTool
id: touch
baseCommand: [touch, touchedfile.txt]
inputs: {}
outputs:
    example_out:
        type: File
        outputBinding:
            glob: touchedfile.txt
