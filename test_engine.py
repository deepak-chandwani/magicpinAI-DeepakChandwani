import os, sys, json
sys.path.insert(0, os.path.dirname(__file__))

from ranker import SignalRanker
from composer import Composer
from conversation import classify, next_reply


def load_seed():
    root = os.path.dirname(os.path.dirname(__file__))
    merchants = json.load(open(os.path.join(root, "dataset", "merchants_seed.json")))['merchants']
    customers = json.load(open(os.path.join(root, "dataset", "customers_seed.json")))['customers']
    triggers = json.load(open(os.path.join(root, "dataset", "triggers_seed.json")))['triggers']
    return merchants, customers, triggers


def test_ranker_prefers_planning():
    merchants, customers, triggers = load_seed()
    m = next(x for x in merchants if x['merchant_id'] == 'm_008_zenyoga_gym_chennai')
    t = next(x for x in triggers if x['kind'] == 'active_planning_intent')
    c = {'slug': 'gyms'}
    d = SignalRanker().rank(c, m, t)
    assert d.send and d.score >= 90


def test_customer_without_consent_is_blocked():
    r = SignalRanker()
    d = r.rank({'slug':'gyms'}, {'merchant_id':'m1'}, {'id':'t1','kind':'customer_lapsed_hard','scope':'customer'}, {'customer_id':'c1'})
    assert d.send is False


def test_reply_intents():
    assert classify('Thank you for contacting us. Our team will get back to you.') == 'auto_reply'
    assert classify('No thanks, stop') == 'negative'
    assert classify('Yes, go ahead') == 'affirmative'
    assert next_reply('No thanks')['action'] == 'end'
    assert next_reply('Yes, do it')['action'] == 'send'


def test_composer_uses_real_offer():
    merchants, customers, triggers = load_seed()
    m = next(x for x in merchants if x['merchant_id'] == 'm_005_pizzajunction_restaurant_delhi')
    t = next(x for x in triggers if x['kind'] == 'ipl_match_today')
    out = Composer().compose({'slug':'restaurants'}, m, t)
    assert out['body']
    assert 'Buy 1 Pizza' in out['body'] or 'BOGO' in out['body'] or 'existing' in out['rationale'].lower()
