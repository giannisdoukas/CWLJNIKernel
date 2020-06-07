cwlVersion: v1.1
class: CommandLineTool
baseCommand: tar
arguments: ["-cvf"]
id: compress
inputs:
  to_compress:
    type:
      type: array
      items: File
    inputBinding:
        position: 2
  tarname:
    type: string
    inputBinding:
      position: 1
    default: "data.tar.gz"
outputs:
  tarfile:
    type: File
    outputBinding:
      glob: "*.tar.gz"
