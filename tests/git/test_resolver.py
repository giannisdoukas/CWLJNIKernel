import os
import tempfile
import unittest
from pathlib import Path

from git.CWLGitResolver import CWLGitResolver


class GitResolverTest(unittest.TestCase):
    def test_resolve(self):
        git_dir = Path(tempfile.mkdtemp())
        git_resolver = CWLGitResolver(
            git_dir,
            "https://github.com/giannisdoukas/CWLJNIKernel/blob/dev/tests/cwl/3stepWorkflow.cwl")
        self.assertListEqual(
            sorted([
                os.path.join(git_dir, f) for f in
                ['tests/cwl/3stepWorkflow.cwl', 'tests/cwl/head.cwl', 'tests/cwl/grep.cwl']
            ]),
            sorted(git_resolver.resolve())
        )


if __name__ == '__main__':
    unittest.main()
