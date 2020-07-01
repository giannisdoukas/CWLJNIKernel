from typing import Dict, Iterable, Optional

from pygtrie import CharTrie


class AutoCompleteEngine:
    """
    AutoCompleteEngine generates suggestions given a users input.
    """

    def __init__(self, magic_commands: Optional[Iterable]):
        self._commands_trie = CharTrie()
        if magic_commands is not None:
            for magic in magic_commands:
                self.add_magic_command(magic)

    def suggest(self, code: str, cursor_pos: int) -> Dict:
        """
        @param code: string contains the current state of the user's input. It could be a CWL file
        or magic commands.
        @param cursor_pos: current position of cursor
        @return: {'matches': ['MATCH1', 'MATCH1'],
                'cursor_end': ,
                'cursor_start': , }
        """
        cursor_end, cursor_start, token = self._parse(code, cursor_pos)
        if token == '%':
            token = ''
        try:
            matches = list(set(self._commands_trie.values(prefix=token)))
            matches.sort(key=len)
        except KeyError:
            matches = []
            cursor_end = cursor_pos
            cursor_start = cursor_pos
        return {
            'matches': matches,
            'cursor_end': cursor_end,
            'cursor_start': cursor_start
        }

    @classmethod
    def _parse(cls, code, cursor_pos):
        code_length = len(code)
        token_ends_at = code.find(" ", cursor_pos)
        cursor_end = min(token_ends_at + 1, code_length - 1)
        if token_ends_at == -1:
            token_ends_at = code_length - 1
            cursor_end = code_length
        token_starts_at = code.rfind(" ", 0, cursor_pos)
        cursor_start = token_starts_at + 1
        if token_starts_at == -1:
            token_starts_at = 0
            cursor_start = cursor_pos
        token = code[token_starts_at:token_ends_at + 1].strip().upper()
        return cursor_end, cursor_start, token

    def add_magic_command(self, magic_command: str):
        for i in range(1, len(magic_command) + 1):
            self._commands_trie[magic_command[-i:].upper()] = magic_command
