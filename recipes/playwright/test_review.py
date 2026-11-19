import contextlib
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import uuid

import review


class ReviewTests(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.candidate = Path(directory.name) / 'observed.candidate.json'
        self.document = {
            'kind': 'cleanapp-playwright-candidate',
            'fixture': False,
            'report': {
                'title': 'Local QA test',
                'description': 'A local test checks the approval boundary.',
                'url': 'https://shop.example.test/checkout',
                'source_id': str(uuid.uuid4()),
                'handling': {'publication': 'private', 'notices': 'none'},
            },
        }

    def invoke(self, *args, tty=False, response=''):
        self.candidate.write_text(json.dumps(self.document), encoding='utf-8')
        terminal = io.StringIO()
        with contextlib.ExitStack() as contexts:
            contexts.enter_context(patch('sys.stdin.isatty', return_value=tty))
            contexts.enter_context(contextlib.redirect_stdout(terminal))
            contexts.enter_context(contextlib.redirect_stderr(io.StringIO()))
            contexts.enter_context(patch.object(terminal, 'isatty', return_value=tty))
            answer = patch('builtins.input', side_effect=response) if callable(response) else patch('builtins.input', return_value=response)
            contexts.enter_context(answer)
            network = contexts.enter_context(patch.object(review.client, 'main', side_effect=self.capture))
            result = review.main([str(self.candidate), *args])
        return result, terminal.getvalue(), network.call_count

    def capture(self, arguments):
        self.sent = json.loads(Path(arguments[1]).read_text(encoding='utf-8'))
        self.arguments = arguments
        return 0

    def test_blocks_fixture_noninteractive_and_unapproved_writes(self):
        self.assertEqual(self.invoke('--send', response='SEND PRIVATE')[::2], (2, 0))
        self.assertEqual(self.invoke('--send', tty=True, response='yes')[::2], (0, 0))
        self.document['fixture'] = True
        self.assertEqual(self.invoke('--send', tty=True, response='SEND PRIVATE')[::2], (2, 0))
        self.assertEqual(self.invoke('--status')[::2], (2, 0))

    def test_sends_exact_reviewed_payload_even_if_candidate_changes(self):
        def approve(_prompt):
            self.candidate.write_text('changed after review', encoding='utf-8')
            return 'SEND PRIVATE'

        result, output, calls = self.invoke('--send', tty=True, response=approve)
        self.assertEqual((result, calls), (0, 1))
        self.assertIn(json.dumps(self.document['report'], indent=2), output)
        self.assertEqual(self.sent, self.document['report'])
        self.assertEqual(self.arguments[2:], ['--receipt-file', str(self.candidate.with_name('observed.receipt.json')), '--submit'])


if __name__ == '__main__':
    unittest.main()
