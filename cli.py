import click
from gsuite_update_script import run


@click.command()
def update():
    run.main()

if __name__ == '__main__':
    update()