# -*- coding: utf-8 -*- 
 
import click 
import zipfile 
from pathlib import Path 
 
@click.group() 
@click.version_option(version="1.0.0", prog_name="Cloud Backup CLI") 
def cli(): 
    """Cloud Backup CLI""" 
    pass 
 
@cli.command() 
def test(): 
    """Test command""" 
    click.echo("Cloud Backup CLI is working!") 
 
@cli.command() 
@click.argument("source") 
@click.option("--output", "-o", default="backup.zip") 
def backup(source, output): 
    """Create backup""" 
    source_path = Path(source) 
    if not source_path.exists(): 
        click.echo(f"Error: {source} not found") 
        return 
 
    with zipfile.ZipFile(output, "w", zipfile.ZIP_DEFLATED) as zipf: 
        if source_path.is_file(): 
            zipf.write(source_path, source_path.name) 
            click.echo(f"Added file: {source_path.name}") 
        else: 
            for file in source_path.rglob("*"): 
                if file.is_file(): 
                    rel_path = file.relative_to(source_path) 
                    zipf.write(file, rel_path) 
                    click.echo(f"Added: {rel_path}") 
 
    click.echo(f"Backup created: {output}") 
 
def main(): 
    cli() 
