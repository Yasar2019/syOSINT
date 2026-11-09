"""Explicit local retention CLI. Preview opens an existing migrated DB only."""
import argparse
import json
import os
from datetime import UTC, datetime
from pathlib import Path
from sqlalchemy import create_engine
from .retention import run_retention, place_hold, release_hold


class SafeParser(argparse.ArgumentParser):
    def error(self, message):
        raise ValueError('invalid retention request')


def run_cli(argv):
    parser = SafeParser(prog='syosint retention')
    commands = parser.add_subparsers(dest='command',required=True)
    commands.add_parser('preview')
    commands.add_parser('run').add_argument('--apply',action='store_true',required=True)
    hold = commands.add_parser('hold')
    hold.add_argument('--kind',choices=('intake','media','quarantine'),required=True)
    hold.add_argument('--id',type=int,required=True); hold.add_argument('--reason',required=True)
    release = commands.add_parser('release')
    release.add_argument('--id',type=int,required=True); release.add_argument('--reason',required=True)
    try:
        args = parser.parse_args(argv)
        root = Path(__file__).resolve().parents[3]
        path = Path(os.environ.get('SYOSINT_DB_PATH',str(root/'private-data/syosint.sqlite3')))
        if not path.is_file() or (args.command == 'run' and os.environ.get('SYOSINT_RETENTION_APPLY') != '1'):
            raise ValueError()
        # mode=rw atomically prevents accidental creation, including a path removal race.
        engine = create_engine(f'sqlite:///file:{path.absolute()}?mode=rw&uri=true')
        now = datetime.now(UTC)
        try:
            if args.command == 'hold': result = place_hold(engine,args.kind,args.id,args.reason,now)
            elif args.command == 'release': result = release_hold(engine,args.id,args.reason,now)
            else:
                private = Path(os.environ.get('SYOSINT_PRIVATE_DIR',str(root/'private-data')))
                result = run_retention(engine,private.absolute()/'telegram/media',now,apply=args.command=='run')
            print(json.dumps(result,default=str,sort_keys=True))
            return 0
        finally:
            engine.dispose()
    except SystemExit:
        print('{"error":"invalid retention request"}'); return 2
    except Exception:
        print('{"error":"retention unavailable"}'); return 2
