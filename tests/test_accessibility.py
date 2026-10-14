from tests.conftest import login
from app.utils.accessibility import audit_html, audit_application_routes


def test_audit_html_catches_violations():
    # Bad HTML: missing lang, empty title, missing main, skipped heading, unlabeled button
    bad_html = """
    <!doctype html>
    <html>
      <head><title></title></head>
      <body>
        <h1>Title</h1>
        <h3>Skipped heading</h3>
        <button></button>
        <img src="test.png">
      </body>
    </html>
    """
    res = audit_html(bad_html, url_label='/bad')
    assert res['passed'] is False
    assert res['violations_count'] >= 4
    rules = [v['rule'] for v in res['violations']]
    assert 'html_lang' in rules
    assert 'page_title' in rules
    assert 'landmarks' in rules
    assert 'button_name' in rules
    assert 'image_alt' in rules


def test_audit_html_passes_compliant_page():
    good_html = """
    <!doctype html>
    <html lang="en">
      <head><title>Dashboard · CampusHub</title></head>
      <body>
        <a href="#main-content" class="skip-link">Skip to main content</a>
        <header role="banner">
          <button aria-label="Menu">☰</button>
        </header>
        <main id="main-content" role="main">
          <h1>Dashboard</h1>
          <h2>Recent Activity</h2>
          <button type="button">Save</button>
        </main>
      </body>
    </html>
    """
    res = audit_html(good_html, url_label='/good')
    assert res['passed'] is True
    assert res['violations_count'] == 0
    assert res['passes_count'] >= 5


def test_base_template_accessibility_features(client, student):
    login(client)
    res = client.get('/dashboard')
    assert res.status_code == 200
    html = res.data.decode('utf-8')

    # Skip to content link
    assert 'class="skip-link"' in html
    assert 'href="#main-content"' in html

    # Main landmark
    assert 'id="main-content"' in html
    assert 'role="main"' in html

    # Menu button accessible label
    assert 'aria-label="Toggle navigation menu"' in html

    # Notification icon link accessible label
    assert 'aria-label="Notifications"' in html


def test_automated_audit_all_routes(client, student):
    report = audit_application_routes(client, student_login_fn=login)
    for r in report['results']:
        if not r['passed']:
            print(f"FAILED: {r['url']}: {r['violations']}")
    assert report['overall_passed'] is True, f"Found {report['total_violations']} violations: {report['results']}"



def test_cli_accessibility_audit(app, student):
    runner = app.test_cli_runner()
    result = runner.invoke(args=['accessibility-audit'])
    assert result.exit_code == 0
    assert 'ACCESSIBILITY AUDIT' in result.output
    assert 'PASS' in result.output


def test_css_accessibility_features(client):
    res = client.get('/static/css/style.css')
    assert res.status_code == 200
    css = res.data.decode('utf-8')

    # Focus indicator
    assert ':focus-visible' in css

    # Skip link styling
    assert '.skip-link' in css

    # Reduced motion support
    assert 'prefers-reduced-motion' in css
