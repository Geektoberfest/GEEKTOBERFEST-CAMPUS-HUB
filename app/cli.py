import click
from flask.cli import with_appcontext
from app.utils.accessibility import audit_application_routes


def register_cli(app):
    @app.cli.command('accessibility-audit')
    @with_appcontext
    def a11y_audit_cmd():
        """Run automated accessibility audit across application pages."""
        from tests.conftest import login
        client = app.test_client()
        report = audit_application_routes(client, student_login_fn=login)
        click.echo("=" * 60)
        click.echo("  ACCESSIBILITY AUDIT (WCAG 2.1 COMPLIANCE)")
        click.echo("=" * 60)
        for r in report['results']:
            status_sym = "✓ PASS" if r['passed'] else "✗ FAIL"
            click.echo(f"[{status_sym}] {r['url']} (Passed: {r['passes_count']}, Violations: {r['violations_count']})")
            for v in r['violations']:
                click.echo(f"    • [{v['rule']}] {v['message']}")
        click.echo("-" * 60)
        click.echo(f"Total Routes Audited: {report['routes_audited']}")
        click.echo(f"Total Passing Checks: {report['total_passes']}")
        click.echo(f"Total Violations: {report['total_violations']}")
        click.echo("=" * 60)
        if not report['overall_passed']:
            raise click.Abort()
