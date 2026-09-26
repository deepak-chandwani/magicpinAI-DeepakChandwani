import os, sys, json
sys.path.insert(0, os.path.dirname(__file__))
from app import app, store

ROOT = os.path.dirname(os.path.dirname(__file__))

def test_health():
    c = app.test_client()
    r = c.get('/v1/healthz')
    assert r.status_code == 200
    assert r.json['status'] == 'ok'


def test_context_versioning():
    c = app.test_client()
    payload = {'scope':'category','context_id':'test-cat','version':1,'payload':{'slug':'dentists'}}
    assert c.post('/v1/context', json=payload).status_code == 200
    assert c.post('/v1/context', json=payload).status_code == 409
    newer = dict(payload); newer['version'] = 2
    assert c.post('/v1/context', json=newer).status_code == 200
