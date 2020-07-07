import unittest

from cwlkernel.AutoCompleteEngine import AutoCompleteEngine
from cwlkernel.CWLKernel import CWLKernel


class TestAutoCompleteEngine(unittest.TestCase):
    maxDiff = None

    def test_suggest_magics(self):
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

        code = "% foo\n% new"
        suggestion = auto_complete_engine.suggest(code, 9)
        self.assertSetEqual(
            {c for c in CWLKernel._magic_commands.keys() if c.startswith("new")},
            set(suggestion.pop('matches'))
        )
        self.assertDictEqual({'cursor_start': 8, 'cursor_end': 11}, suggestion)

    def test_suggest_magics_args(self):
        auto_complete_engine = CWLKernel._auto_complete_engine

        @CWLKernel.register_magics_suggester('execute')
        def suggester1(*args, **kwargs):
            return ['foo', 'bar', 'foobar']

        code = "% execute "
        self.assertDictEqual(
            {'matches': ['foo', 'bar', 'foobar'], 'cursor_start': len(code),
             'cursor_end': len(code)},
            auto_complete_engine.suggest(code, len(code))
        )

        @CWLKernel.register_magics_suggester('execute')
        def suggester2(query_token, *args, **kwargs):
            return [
                x for x in ['foo', 'bar', 'foobar']
                if x.upper().startswith(query_token.upper())
            ]
        code = "% execute f"
        self.assertDictEqual(
            {'matches': ['foo', 'foobar'], 'cursor_start': 10,
             'cursor_end': 11},
            auto_complete_engine.suggest(code, 11)
        )

        code = "% foo\n% execute f"
        self.assertDictEqual(
            {'matches': ['foo', 'foobar'], 'cursor_start': 16,
             'cursor_end': 17},
            auto_complete_engine.suggest(code, 17)
        )


if __name__ == '__main__':
    unittest.main()
