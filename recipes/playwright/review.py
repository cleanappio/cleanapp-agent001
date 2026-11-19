#!/usr/bin/env python3
"""Review one Playwright candidate offline, or explicitly approve a private send."""

import argparse
import json
from pathlib import Path
import sys
import tempfile
from urllib.parse import urlsplit

recipe = Path(__file__).resolve().parent
client_directory = recipe / 'support'
if not (client_directory / 'report.py').is_file():
    client_directory = recipe.parent.parent / 'openclaw-skill'
if not (client_directory / 'report.py').is_file():
    raise SystemExit('CleanApp QA: missing support/report.py. Install the complete adapter tarball.')
sys.path.insert(0, str(client_directory))
import report as client


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('candidate', type=Path)
    modes = parser.add_mutually_exclusive_group()
    modes.add_argument('--send', action='store_true', help='Review and approve the exact report in a terminal')
    modes.add_argument('--status', action='store_true', help='Read status from the private receipt')
    parser.add_argument('--retry', action='store_true', help='With --send, retry the unchanged report after uncertain delivery')
    args = parser.parse_args(argv)
    if args.retry and not args.send:
        parser.error('--retry requires --send')
    receipt = args.candidate.with_name(args.candidate.stem.removesuffix('.candidate') + '.receipt.json')

    try:
        candidate = json.loads(args.candidate.read_text(encoding='utf-8'))
        if not isinstance(candidate, dict) or candidate.get('kind') != 'cleanapp-playwright-candidate':
            raise client.ClientError('Expected a CleanApp Playwright candidate file')
        report = client.validate_payload(candidate.get('report'))
        required = {'title', 'description', 'url', 'source_id', 'handling'}
        if set(report) != required or report['handling'] != {'publication': 'private', 'notices': 'none'}:
            raise client.ClientError('Expected a complete Playwright report for private review with notices off')

        url = urlsplit(report['url'])
        if url.query or url.fragment:
            raise client.ClientError('Remove the source URL query or fragment before review')
        fixture = (candidate.get('fixture') is not False or url.scheme != 'https'
                   or url.hostname in {'localhost', '127.0.0.1', '::1'})
        if (args.send or args.status) and fixture:
            raise client.ClientError('Fixture candidates are offline only')
        if args.status:
            return client.main(['--status', '--receipt-file', str(receipt)])
        if args.send and not (sys.stdin.isatty() and sys.stdout.isatty()):
            raise client.ClientError('Open a private interactive terminal to approve this send')

        payload = json.dumps(report, ensure_ascii=False, indent=2)
        print(payload, flush=True)
        if not args.send:
            if fixture:
                print('Fixture candidate. Nothing sent.', file=sys.stderr)
            return 0

        print('Review this exact report. CleanApp will receive and store it for private review with notices off.')
        if input('Type SEND PRIVATE to approve transmission: ') != 'SEND PRIVATE':
            print('Nothing sent.')
            return 0

        # Submit the bytes just shown, even if another process edits the candidate during review.
        with tempfile.NamedTemporaryFile(mode='w', encoding='utf-8') as approved:
            approved.write(payload)
            approved.flush()
            command = ['--input', approved.name, '--receipt-file', str(receipt), '--submit']
            return client.main(command + (['--retry'] if args.retry else []))
    except (client.ClientError, ValueError, OSError, EOFError) as error:
        print(f'CleanApp QA: {error}', file=sys.stderr)
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
