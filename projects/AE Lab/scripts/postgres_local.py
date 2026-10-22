"""Start/stop only the project-owned PostgreSQL cluster; no launch service."""
import argparse
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import psycopg
from psycopg.conninfo import make_conninfo

ROOT=Path(__file__).resolve().parents[1]

def binary(name):
    configured=os.environ.get('AE_LAB_PG_BIN')
    candidates=[Path(configured)/name] if configured else []
    found=shutil.which(name)
    if found:candidates.append(Path(found))
    candidates += [Path('/opt/homebrew/opt/postgresql@17/bin')/name,Path('/usr/lib/postgresql/17/bin')/name]
    for candidate in candidates:
        if candidate.is_file():return str(candidate)
    raise RuntimeError('PostgreSQL 17 binaries required; brew install postgresql@17 or set AE_LAB_PG_BIN.')

def run(args):
    result=subprocess.run(args,text=True,capture_output=True)
    if result.returncode:raise RuntimeError(result.stderr or result.stdout)
    return result.stdout

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('action',choices=['start','stop','status'])
    parser.add_argument('--state-dir',type=Path,default=ROOT/'.lab')
    parser.add_argument('--port',type=int,default=55432)
    args=parser.parse_args(); root=args.state_dir.resolve(); cluster=root/'postgres'; socket=root/'pgsocket'
    root.mkdir(parents=True,exist_ok=True);socket.mkdir(exist_ok=True,mode=0o700)
    if len(str(socket))>85:raise RuntimeError('State directory too long for a Unix socket; select a shorter project-local profile.')
    if args.action=='stop':
        if not (cluster/'PG_VERSION').exists():raise RuntimeError('No Lab-owned cluster exists.')
        print(run([binary('pg_ctl'),'-D',str(cluster),'-m','fast','-w','stop']));return
    if args.action=='status':
        print(run([binary('pg_ctl'),'-D',str(cluster),'status']));return
    if not (cluster/'PG_VERSION').exists():
        run([binary('initdb'),'-D',str(cluster),'--username=ae_lab_admin','--auth-local=trust','--auth-host=reject','--encoding=UTF8','--no-locale'])
    # A running cluster's stored connection parameters take precedence over new flags.
    config=root/'postgres.json'
    running=subprocess.run([binary('pg_ctl'),'-D',str(cluster),'status'],capture_output=True).returncode==0
    if not running:
        run([binary('pg_ctl'),'-D',str(cluster),'-l',str(root/'postgres.log'),'-o',f"-k '{socket}' -p {args.port} -c listen_addresses=''",'-w','start'])
    if running and config.exists():
        conn=json.loads(config.read_text())['dsn']
    else:
        admin=make_conninfo(host=str(socket),port=args.port,user='ae_lab_admin',dbname='postgres')
        with psycopg.connect(admin,autocommit=True) as db:
            if not db.execute("SELECT 1 FROM pg_database WHERE datname='ae_lab_sql'").fetchone():db.execute('CREATE DATABASE ae_lab_sql')
        conn=make_conninfo(host=str(socket),port=args.port,user='ae_lab_admin',dbname='ae_lab_sql')
        config.write_text(json.dumps({'dsn':conn,'cluster':str(cluster),'socket':str(socket)},indent=2)+'\n');config.chmod(0o600)
    sys.path.insert(0,str(ROOT))
    from lab.sql_lab.postgres import Postgres
    print(json.dumps(Postgres(root).bootstrap(),indent=2))

if __name__=='__main__':
    try:main()
    except (RuntimeError,OSError,psycopg.Error) as e:sys.exit(str(e))
