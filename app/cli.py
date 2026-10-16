import click
from flask.cli import with_appcontext
from app.services.backup import create_backup, restore_backup


def register_cli(app):
    @app.cli.command('db-backup')
    @click.option('--output', '-o', default=None, help='Output path for the backup file.')
    @click.option('--format', '-f', type=click.Choice(['json', 'sqlite'], case_sensitive=False), default='json', help='Backup format: json or sqlite.')
    @with_appcontext
    def db_backup_cmd(output, format):
        """Create a backup of the database."""
        try:
            result = create_backup(output_path=output, format=format)
            click.echo(f"✓ Backup created successfully ({result['format']}) at: {result['path']}")
            if 'counts' in result:
                counts_str = ', '.join(f"{k}: {v}" for k, v in result['counts'].items())
                click.echo(f"  Records backed up: {counts_str}")
        except Exception as e:
            click.echo(f"✗ Backup failed: {e}", err=True)
            raise click.Abort()

    @app.cli.command('db-restore')
    @click.option('--input', '-i', 'input_path', required=True, help='Path to the backup file to restore.')
    @click.option('--yes', '-y', is_flag=True, help='Skip confirmation prompt.')
    @click.option('--no-safety-backup', is_flag=True, help='Skip creating an automatic pre-restore safety backup.')
    @with_appcontext
    def db_restore_cmd(input_path, yes, no_safety_backup):
        """Restore the database from a backup file."""
        if not yes:
            click.confirm(
                "WARNING: Restoring will overwrite existing database records.\n"
                "Are you sure you want to proceed?",
                abort=True
            )
        try:
            result = restore_backup(input_path=input_path, create_safety_backup=not no_safety_backup)
            click.echo(f"✓ Database restored successfully from: {result['path']}")
            if result.get('safety_backup_path'):
                click.echo(f"  Safety backup created at: {result['safety_backup_path']}")
            if 'restored_counts' in result:
                counts_str = ', '.join(f"{k}: {v}" for k, v in result['restored_counts'].items())
                click.echo(f"  Records restored: {counts_str}")
        except Exception as e:
            click.echo(f"✗ Restore failed: {e}", err=True)
            raise click.Abort()

    # Aliases
    @app.cli.command('backup-db', hidden=True)
    @click.option('--output', '-o', default=None)
    @click.option('--format', '-f', default='json')
    @with_appcontext
    def backup_db_alias(output, format):
        """Alias for db-backup."""
        db_backup_cmd.callback(output, format)

    @app.cli.command('restore-db', hidden=True)
    @click.option('--input', '-i', 'input_path', required=True)
    @click.option('--yes', '-y', is_flag=True)
    @click.option('--no-safety-backup', is_flag=True)
    @with_appcontext
    def restore_db_alias(input_path, yes, no_safety_backup):
        """Alias for db-restore."""
        db_restore_cmd.callback(input_path, yes, no_safety_backup)
