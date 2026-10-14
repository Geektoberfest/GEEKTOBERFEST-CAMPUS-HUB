from tests.conftest import login
from app.extensions import db
from app.models import User
from app.services.i18n import translate, get_current_language, SUPPORTED_LANGUAGES


def test_translate_helper(app):
    with app.test_request_context():
        # English
        assert translate('nav_dashboard', lang='en') == 'Dashboard'
        assert translate('nav_tasks', lang='en') == 'Tasks'

        # Spanish
        assert translate('nav_dashboard', lang='es') == 'Panel Principal'
        assert translate('nav_tasks', lang='es') == 'Tareas'

        # French
        assert translate('nav_dashboard', lang='fr') == 'Tableau de bord'
        assert translate('nav_tasks', lang='fr') == 'Tâches'

        # German
        assert translate('nav_dashboard', lang='de') == 'Übersicht'
        assert translate('nav_tasks', lang='de') == 'Aufgaben'

        # Hindi
        assert translate('nav_dashboard', lang='hi') == 'डैशबोर्ड'
        assert translate('nav_tasks', lang='hi') == 'कार्य'

        # Fallback to key or default
        assert translate('non_existent_key', default='Fallback Text', lang='es') == 'Fallback Text'
        assert translate('non_existent_key', lang='en') == 'non_existent_key'


def test_set_language_route(client, app, student):
    login(client)

    # Change to Spanish
    res = client.get('/set-language/es', follow_redirects=True)
    assert res.status_code == 200

    # User in db should have language updated
    with app.app_context():
        user = db.session.get(User, student)
        assert user.language == 'es'

    # Dashboard should now render Spanish navigation
    assert 'Panel Principal'.encode('utf-8') in res.data
    assert 'Tareas'.encode('utf-8') in res.data

    # Change to French
    res = client.get('/set-language/fr', follow_redirects=True)
    assert res.status_code == 200
    assert 'Tableau de bord'.encode('utf-8') in res.data

    # Change to Hindi
    res = client.get('/set-language/hi', follow_redirects=True)
    assert res.status_code == 200
    assert 'डैशबोर्ड'.encode('utf-8') in res.data


def test_query_param_language_override(client, student):
    login(client)
    res = client.get('/dashboard?lang=de')
    assert res.status_code == 200
    assert 'Übersicht'.encode('utf-8') in res.data


def test_api_translations(client):
    res = client.get('/api/translations?lang=es')
    assert res.status_code == 200
    data = res.get_json()['data']
    assert data['language'] == 'es'
    assert data['translations']['nav_dashboard'] == 'Panel Principal'
    assert 'en' in data['supported_languages']
    assert 'es' in data['supported_languages']


def test_api_set_user_language(client, app, student):
    login(client)

    # Valid update
    res = client.put('/api/user/language', json={'language': 'de'})
    assert res.status_code == 200
    assert res.get_json()['data']['language'] == 'de'

    with app.app_context():
        user = db.session.get(User, student)
        assert user.language == 'de'

    # Invalid language
    res = client.put('/api/user/language', json={'language': 'invalid_lang'})
    assert res.status_code == 400


def test_profile_update_language(client, app, student):
    login(client)
    res = client.post('/profile', data={
        'name': 'Test Student',
        'department': 'CS',
        'year': '3',
        'language': 'fr'
    }, follow_redirects=True)
    assert res.status_code == 200

    with app.app_context():
        user = db.session.get(User, student)
        assert user.language == 'fr'
