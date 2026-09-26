"""Static quality checks: provenance, CTA discipline, empty messages, obvious hallucination risk."""
import json, os, re

ROOT = os.path.dirname(__file__)
EXP = os.path.join(ROOT, 'expanded')

CTA_PATTERNS = [r'\breply\s+yes\b', r'\breply\s+confirm\b', r'\breply\s+stop\b', r'\bwant me to\b', r'\bshall i\b']
BAD_GENERIC = ['amazing deal', 'limited time offer', 'guaranteed', 'everyone will', '100%']


def main():
    rows = [json.loads(x) for x in open(os.path.join(ROOT, 'submission.jsonl'), encoding='utf-8') if x.strip()]
    problems = []
    for row in rows:
        body = row['body']
        low = body.lower()
        if not body.strip(): problems.append((row['test_id'], 'empty body'))
        if len(re.findall(r'\?', body)) > 1: problems.append((row['test_id'], 'multiple question marks / CTA risk'))
        for bad in BAD_GENERIC:
            if bad in low: problems.append((row['test_id'], f'generic/risky phrase: {bad}'))
        if row['send_as'] == 'merchant_on_behalf' and row['cta'] == 'open_ended':
            problems.append((row['test_id'], 'customer message should usually have binary CTA'))
    print(f'Rows: {len(rows)}')
    if problems:
        print('Potential issues:')
        for p in problems: print('-', p[0], p[1])
    else:
        print('No obvious static quality issues found.')


if __name__ == '__main__': main()
