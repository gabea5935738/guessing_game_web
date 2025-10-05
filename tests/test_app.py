# To run test, run "pytest tests/ --maxfail=3 --disable-warnings -v" in terminal
import sys
import os
import pytest

# Ensure the app module can be imported
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from app import app as flask_app

@pytest.fixture
def client():
    """Flask test client fixture."""
    flask_app.config['TESTING'] = True
    with flask_app.test_client() as client:
        with flask_app.app_context():
            yield client

def post_difficulty(client, difficulty):
    """Helper to post a difficulty selection."""
    return client.post('/', data={'difficulty': difficulty}, follow_redirects=True)

@pytest.mark.parametrize("route,expected", [
    ("/", b"Select"),
    ("/shop", b"Shop"),
])
def test_routes_load(client, route, expected):
    """Test that key routes load and contain expected text."""
    response = client.get(route)
    assert response.status_code == 200
    assert expected in response.data or b'difficulty' in response.data or b'buy' in response.data

def test_reset_route(client):
    """Test that the reset route clears session and redirects to homepage."""
    response = client.get('/reset', follow_redirects=True)
    assert response.status_code == 200
    assert b'Select' in response.data or b'difficulty' in response.data

def test_post_difficulty_sets_session(client):
    """Test that posting a difficulty sets up the game session."""
    response = post_difficulty(client, 'easy')
    assert response.status_code == 200
    assert b'guess' in response.data or b'number' in response.data

class TestGame:
    def test_game_page_loads(self, client):
        """Test that the game page loads after selecting a difficulty."""
        post_difficulty(client, 'easy')
        response = client.get('/game')
        assert response.status_code == 200
        assert b'guess' in response.data or b'number' in response.data

    def test_shop_purchase_invalid(self, client):
        """Test that shop returns error message if not enough points."""
        post_difficulty(client, 'easy')
        response = client.post('/shop', data={'item': 'hint'}, follow_redirects=True)
        assert b'Not enough points' in response.data or b'invalid item' in response.data
