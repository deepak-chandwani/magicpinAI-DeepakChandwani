import json, os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "bot"))
from composer import Composer

ROOT = os.path.dirname(__file__)
EXP = os.path.join(ROOT, "expanded")


def load_dir(folder, key):
    result = {}
    for filename in os.listdir(os.path.join(EXP, folder)):
        if not filename.endswith('.json'):
            continue
        with open(os.path.join(EXP, folder, filename), encoding='utf-8') as f:
            item = json.load(f)
        if key in item:
            result[item[key]] = item
    return result


def main():
    cats = load_dir('categories', 'slug')
    merchants = load_dir('merchants', 'merchant_id')
    customers = load_dir('customers', 'customer_id')
    triggers = load_dir('triggers', 'id')
    with open(os.path.join(EXP, 'test_pairs.json'), encoding='utf-8') as f:
        pairs = json.load(f)['pairs']

    composer = Composer()
    out = []
    for pair in pairs:
        trigger = triggers[pair['trigger_id']]
        merchant = merchants[pair['merchant_id']]
        category = cats[merchant['category_slug']]
        customer = customers.get(pair.get('customer_id'))
        result = composer.compose(category, merchant, trigger, customer)
        out.append({
            'test_id': pair['test_id'],
            'body': result['body'],
            'cta': result['cta'],
            'send_as': result['send_as'],
            'suppression_key': result['suppression_key'],
            'rationale': result['rationale'],
        })

    with open(os.path.join(ROOT, 'submission.jsonl'), 'w', encoding='utf-8') as f:
        for row in out:
            f.write(json.dumps(row, ensure_ascii=False) + '\n')
    print(f'Wrote {len(out)} lines to submission.jsonl')


if __name__ == '__main__':
    main()
