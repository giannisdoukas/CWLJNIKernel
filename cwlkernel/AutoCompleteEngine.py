import re
from typing import Dict, Iterable, Optional, Callable, Tuple, List

from pygtrie import CharTrie


class AutoCompleteEngine:
    """
    AutoCompleteEngine generates suggestions given a users input.
    """

    def __init__(self, magic_commands: Optional[Iterable[str]]):
        self._magics_args_suggesters: Dict[str, Callable] = {}
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
        matches = []
        cursor_end = cursor_pos
        cursor_start = cursor_pos
        line_classifier = re.compile(r'(?P<command>^%[ ]+[\w]*)(?P<args>( [\S]*)*)', re.MULTILINE)
        for match in line_classifier.finditer(code):  # type: re.Match
            if match.start('command') <= cursor_pos <= match.end('command'):
                new_cursor_pos = cursor_pos - match.span()[0]
                code = match.group()
                matches, cursor_start, cursor_end = self._suggest_magic_command(code, new_cursor_pos)
                cursor_start += match.span()[0]
                cursor_end += match.span()[0]
            elif match.span()[0] <= cursor_pos <= match.span()[1]:
                new_cursor_pos = cursor_pos - match.start('args')
                code = match.group('args')
                command = match.group('command')[1:].strip()
                matches, cursor_start, cursor_end = self._suggest_magics_arguments(command, code, new_cursor_pos)
                cursor_start += match.start('args')
                cursor_end += match.start('args')
        return {
            'matches': matches,
            'cursor_end': cursor_end,
            'cursor_start': cursor_start
        }

    def _suggest_magic_command(self, code: str, cursor_pos: int) -> Tuple[List[str], int, int]:
        cursor_end, cursor_start, token = self._parse_tokens(code, cursor_pos)
        if token == '%':
            token = ''
        try:
            matches = [m for m in set(self._commands_trie.values(prefix=token))]
            matches.sort(key=len)
        except KeyError:
            matches = []
            cursor_end = cursor_pos
            cursor_start = cursor_pos
        return matches, cursor_start, cursor_end

    def _suggest_magics_arguments(self, command: str, code: str, cursor_pos: int) -> Tuple[List[str], int, int]:
        """Stateless command's arguments suggester"""
        cursor_end, cursor_start, query_token = self._parse_tokens(code, cursor_pos)
        options: List[str] = self._magics_args_suggesters[command](query_token)
        return options, cursor_start, cursor_end

    def add_magic_commands_suggester(self, magic_name: str, suggester: Callable) -> None:
        self._magics_args_suggesters[magic_name] = suggester

    @classmethod
    def _parse_tokens(cls, code, cursor_pos):
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

    def add_magic_command(self, magic_command_name: str):
        for i in range(1, len(magic_command_name) + 1):
            self._commands_trie[magic_command_name[-i:].upper()] = magic_command_name
