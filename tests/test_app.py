import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import pytest
from app import app as flask_app

@pytest.fixture
def client():
    flask_app.config['TESTING'] = True
    with flask_app.test_client() as client:
        with flask_app.app_context():
            yield client

def test_homepage_loads(client):
    response = client.get('/')
    assert response.status_code == 200
    assert b'Select' in response.data or b'difficulty' in response.data

def test_shop_loads(client):
    response = client.get('/shop')
    assert response.status_code == 200
    assert b'Shop' in response.data or b'buy' in response.data

def test_reset_route(client):
    response = client.get('/reset', follow_redirects=True)
    assert response.status_code == 200
    assert b'Select' in response.data or b'difficulty' in response.data

def test_post_difficulty_sets_session(client):
    response = client.post('/', data={'difficulty': 'easy'}, follow_redirects=True)
    assert response.status_code == 200
    # Should redirect to /game or show game page
    assert b'guess' in response.data or b'number' in response.data
