import pathlib, subprocess, sys

DB_PATH = pathlib.Path('data/app.db')
ALEMBIC = ['alembic']

def main():
    if DB_PATH.exists():
        print(f'Removing existing database {DB_PATH}')
        DB_PATH.unlink()
    # Ensure data directory exists
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    # Run upgrade head to apply initial migration
    try:
        subprocess.check_call(ALEMBIC + ['upgrade', 'head'])
        print('Database recreated and migrated to head.')
    except subprocess.CalledProcessError as e:
        print('Failed running alembic upgrade head', e, file=sys.stderr)
        sys.exit(1)

if __name__ == '__main__':
    main()
