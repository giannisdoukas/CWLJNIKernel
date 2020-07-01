import unittest

from cwlkernel.AutoCompleteEngine import AutoCompleteEngine
from cwlkernel.CWLKernel import CWLKernel


class TestAutoCompleteEngine(unittest.TestCase):
    maxDiff = None

    def test_suggest(self):
        auto_complete_engine = AutoCompleteEngine(CWLKernel._magic_commands.keys())
        code = "NOT EXISTING CONTENT"
        self.assertDictEqual(
            {'matches': [], 'cursor_start': len(code) - 1,
             'cursor_end': len(code) - 1},
            auto_complete_engine.suggest(code, len(code) - 1)
        )

        code = "% "
        suggestion = auto_complete_engine.suggest(code, 1)
        self.assertSetEqual(
            set(CWLKernel._magic_commands.keys()),
            set(suggestion.pop('matches'))
        )
        self.assertDictEqual({'cursor_start': 1, 'cursor_end': 1}, suggestion)

        code = "% NEW"
        suggestion = auto_complete_engine.suggest(code, 5)
        self.assertSetEqual(
            {c for c in CWLKernel._magic_commands.keys() if c.startswith("new")},
            set(suggestion.pop('matches'))
        )
        self.assertDictEqual({'cursor_start': 2, 'cursor_end': 5}, suggestion)

        code = "% new"
        suggestion = auto_complete_engine.suggest(code, 3)
        self.assertSetEqual(
            {c for c in CWLKernel._magic_commands.keys() if c.startswith("new")},
            set(suggestion.pop('matches'))
        )
        self.assertDictEqual({'cursor_start': 2, 'cursor_end': 5}, suggestion)


if __name__ == '__main__':
    unittest.main()
