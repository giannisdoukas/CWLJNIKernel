from pathlib import Path

from ruamel.yaml import ruamel


class CWLBuilder:
    _code: str

    def __init__(self):
        self._code = ""

    def append(self, code: str, indent: int = 0) -> None:
        code = '\n'. \
            join([''.join([' ' for _ in range(indent)]) + line
                  for line in code.splitlines()])
        if self._code == "":
            self._code = str(code)
        else:
            self._code += '\n' + str(code)

    def get_current_code(self) -> str:
        return self._code

    def build(self, location: Path) -> None:
        code = ruamel.yaml.round_trip_load(self._code)
        # code = yaml.load(self._code, )
        with location.open('w') as f:
            # yaml.dump(code, f)
            ruamel.yaml.round_trip_dump(code, f)
