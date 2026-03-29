"""System key management commands."""

from __future__ import annotations

import sys

import click


@click.group(name="key")
def key_group() -> None:
    """Manage local Caracal master key lifecycle."""


@key_group.command(name="rotate")
@click.option(
    "--confirm",
    is_flag=True,
    help="Confirm rotation without interactive prompt.",
)
def rotate(confirm: bool) -> None:
    """Rotate local master key and re-wrap all DEKs."""
    if not confirm:
        click.confirm(
            "Rotate local master key and re-wrap all local DEKs?",
            abort=True,
        )

    try:
        from caracal.config.encryption import rotate_master_key

        summary = rotate_master_key(actor="cli")
        click.echo("Master key rotation complete.")
        click.echo(f"  Re-wrapped DEKs : {summary.rewrapped_deks}")
        click.echo(f"  Rotated at      : {summary.rotated_at}")
    except Exception as exc:
        click.echo(f"Error rotating master key: {exc}", err=True)
        sys.exit(1)


@key_group.command(name="status")
def status() -> None:
    """Show current master key and DEK status."""
    try:
        from caracal.config.encryption import get_key_status

        key_status = get_key_status()
        click.echo("Master Key Status")
        click.echo(f"  Home             : {key_status['home']}")
        click.echo(f"  Master key       : {'present' if key_status['master_key_present'] else 'missing'}")
        click.echo(f"  Installation salt: {'present' if key_status['salt_present'] else 'missing'}")
        click.echo(f"  DEKs             : {key_status['dek_count']}")
        click.echo(f"  Key audit log    : {key_status['key_audit_log']}")
    except Exception as exc:
        click.echo(f"Error reading key status: {exc}", err=True)
        sys.exit(1)
