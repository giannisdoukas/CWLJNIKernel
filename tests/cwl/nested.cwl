class: Workflow
cwlVersion: v1.0
id: main
inputs:
- id: inputfile
  type: File
outputs: []
requirements:
  SubworkflowFeatureRequirement: {}
steps:
  head:
    in:
      headinput: inputfile
    out: []
    run:
      baseCommand:
      - head
      class: CommandLineTool
      id: head
      inputs:
      - id: number_of_lines
        inputBinding:
          position: 0
          prefix: -n
        type: int?
      - id: headinput
        inputBinding:
          position: 1
        type: File
      label: head
      outputs:
      - id: headoutput
        type: stdout
      stdout: head.out
  workflow1:
    in:
      inputfile: inputfile
    out: []
    run:
      class: Workflow
      id: w1
      inputs:
      - id: inputfile
        type: File
      outputs: []
      requirements:
        SubworkflowFeatureRequirement: {}
      steps:
        head:
          in:
            headinput: inputfile
          out: [headoutput]
          run:
            baseCommand:
            - head
            class: CommandLineTool
            id: head
            inputs:
            - id: number_of_lines
              inputBinding:
                position: 0
                prefix: -n
              type: int?
            - id: headinput
              inputBinding:
                position: 1
              type: File
            label: head
            outputs:
            - id: headoutput
              type: stdout
            stdout: head.out
        tail:
          in:
            tailinput: head/headoutput
          out: []
          run:
            baseCommand:
            - tail
            class: CommandLineTool
            id: tail
            inputs:
            - id: number_of_lines
              inputBinding:
                position: 0
                prefix: -n
              type: int?
            - id: tailinput
              inputBinding:
                position: 1
              type: File
            label: tail
            outputs:
            - id: tailoutput
              type: stdout
            stdout: tail.out
