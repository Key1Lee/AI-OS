"""Dedicated PostgreSQL fixture warehouse. Never connects to a production DB."""
from __future__ import annotations
from datetime import date, datetime
from decimal import Decimal
import json
import os
from pathlib import Path
from uuid import uuid4
import psycopg
from psycopg import sql
from psycopg.types.json import Jsonb
import sqlglot
from sqlglot import exp
from .datasets import DOMAINS, fixture

class SQLRejected(ValueError):
    pass

SAFE_FUNCTIONS = {'SUM','COUNT','AVG','MIN','MAX','COALESCE','NULLIF','ROW_NUMBER','RANK','DENSE_RANK',
                  'LAG','LEAD','FIRST_VALUE','LAST_VALUE','NTH_VALUE','ABS','ROUND','FLOOR','CEIL',
                  'CAST','TRY_CAST','EXTRACT','DATE_TRUNC','TIMESTAMP_TRUNC','DATE','DATETIME',
                  'GREATEST','LEAST','LOWER','UPPER','TRIM','CONCAT','LENGTH','IF','CASE',
                  'ANONYMOUS','AND','OR','EXISTS'}
SAFE_ANONYMOUS = {'date_trunc','round','length','greatest','least','btrim'}
SAFE_FUNCTIONS |= {'SPLIT_PART','JSON_EXTRACT','JSON_EXTRACT_SCALAR','REGEXP_LIKE','UNNEST',
                   'PERCENTILE_CONT','NTILE','REPLACE','SUBSTRING','TIMEZONE','AT_TIME_ZONE'}
SAFE_ANONYMOUS |= {'jsonb_array_elements','jsonb_array_elements_text','jsonb_typeof'}


def parse_submission(query, allowed):
    if not isinstance(query,str) or not query.strip() or len(query)>10000:
        raise SQLRejected('Submit one SELECT, at most 10,000 characters.')
    try:
        parsed=sqlglot.parse(query,read='postgres')
    except sqlglot.errors.ParseError as exc:
        raise SQLRejected(str(exc)) from exc
    if len(parsed)!=1 or not isinstance(parsed[0],(exp.Select,exp.Union,exp.Intersect,exp.Except)):
        raise SQLRejected('Only one read-only SELECT or SELECT set operation is supported.')
    tree=parsed[0]
    forbidden=(exp.Insert,exp.Update,exp.Delete,exp.Create,exp.Drop,exp.Alter,exp.Command,exp.Into,exp.Lock)
    if any(isinstance(node,forbidden) for node in tree.walk()):
        raise SQLRejected('Writes, SELECT INTO, commands and row locks are not supported.')
    if any(cte.args.get('recursive') for cte in tree.find_all(exp.With)):
        raise SQLRejected('Recursive CTEs are outside the bounded interview runtime.')
    aliases={cte.alias_or_name.lower() for cte in tree.find_all(exp.CTE)}
    sources=set()
    for t in tree.find_all(exp.Table):
        if t.db or t.catalog or t.name.lower() not in set(allowed)|aliases:
            raise SQLRejected('Use only the displayed unqualified source tables and your CTEs.')
        if t.name.lower() in allowed:sources.add(t.name.lower())
    if not sources:
        raise SQLRejected('The answer must calculate from the displayed sources.')
    for f in tree.find_all(exp.Func):
        name=f.sql_name()
        if name not in SAFE_FUNCTIONS or (isinstance(f,exp.Anonymous) and f.name.lower() not in SAFE_ANONYMOUS):
            raise SQLRejected(f'Function {f.name or name} is outside the bounded analytical function set.')
    # Schema-qualified calls, custom operators, and system casts are unsupported.
    for dot in tree.find_all(exp.Dot):
        if isinstance(dot.expression,exp.Func):
            raise SQLRejected('Schema-qualified function calls are unsupported.')
    for cast in tree.find_all(exp.Cast):
        dtype=cast.args.get('to')
        if dtype and dtype.sql(dialect='postgres').lower() in {'regclass','regproc','regprocedure','regtype'}:
            raise SQLRejected('System object casts are unsupported.')
    return tree


def value(v):
    if isinstance(v,Decimal):return int(v) if v==v.to_integral_value() else str(v)
    if isinstance(v,(datetime,date)):return v.isoformat()
    return v

class Postgres:
    def __init__(self, state_root: Path | None = None):
        root=(state_root or Path(__file__).resolve().parents[2]/'.lab').resolve()
        config=root/'postgres.json'
        self.dsn=os.environ.get('AE_LAB_POSTGRES_DSN') or (json.loads(config.read_text())['dsn'] if config.exists() else None)

    def connect(self):
        if not self.dsn:
            raise RuntimeError('PostgreSQL is not configured. Run uv run python scripts/postgres_local.py start.')
        db=psycopg.connect(self.dsn,connect_timeout=5)
        name=db.info.dbname
        if not name.startswith('ae_lab'):
            db.close()
            raise RuntimeError('Use a dedicated database whose name begins ae_lab.')
        return db

    def bootstrap(self):
        with self.connect() as db:
            if not db.execute("SELECT 1 FROM pg_roles WHERE rolname='ae_sql_reader'").fetchone():
                db.execute('CREATE ROLE ae_sql_reader NOLOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOINHERIT NOBYPASSRLS')
            db.execute(sql.SQL('REVOKE CREATE,TEMPORARY ON DATABASE {} FROM PUBLIC').format(sql.Identifier(db.info.dbname)))
            db.execute('REVOKE ALL ON SCHEMA public FROM PUBLIC')
        return self.health()

    def health(self):
        with self.connect() as db:
            version=db.execute('SELECT version()').fetchone()[0]
            return {'dialect':'postgresql','version':version,'database':db.info.dbname,'execution':'real PostgreSQL'}

    def load(self,db,schema,domain,data,models=False):
        definition=DOMAINS[domain]
        db.execute(sql.SQL('CREATE SCHEMA {}').format(sql.Identifier(schema)))
        db.execute(sql.SQL('SET LOCAL search_path TO {},pg_catalog').format(sql.Identifier(schema)))
        for t in definition.tables:
            if t.model_sql:continue
            fields=[sql.SQL('{} {}').format(sql.Identifier(c),sql.SQL(dtype)) for c,dtype in t.columns.items()]
            fields.append(sql.SQL('PRIMARY KEY ({})').format(sql.SQL(',').join(map(sql.Identifier,t.primary_key))))
            for f in t.foreign_keys:
                if f.temporal:continue
                fields.append(sql.SQL('FOREIGN KEY ({}) REFERENCES {} ({})').format(
                    sql.SQL(',').join(map(sql.Identifier,f.columns)),sql.Identifier(f.table),sql.SQL(',').join(map(sql.Identifier,f.target))))
            db.execute(sql.SQL('CREATE TABLE {} ({})').format(sql.Identifier(t.name),sql.SQL(',').join(fields)))
            if data.get(t.name):
                with db.cursor() as cur:
                    cur.executemany(sql.SQL('INSERT INTO {} ({}) VALUES ({})').format(sql.Identifier(t.name),
                        sql.SQL(',').join(map(sql.Identifier,t.columns)),sql.SQL(',').join(sql.Placeholder() for _ in t.columns)),
                        [[Jsonb(r[c]) if t.columns[c]=='jsonb' else r[c] for c in t.columns] for r in data[t.name]])
        if models:
            for t in definition.tables:
                if t.model_sql:
                    db.execute(sql.SQL('CREATE VIEW {} AS ').format(sql.Identifier(t.name))+sql.SQL(t.model_sql))
        db.execute(sql.SQL('GRANT USAGE ON SCHEMA {} TO ae_sql_reader').format(sql.Identifier(schema)))
        db.execute(sql.SQL('GRANT SELECT ON ALL TABLES IN SCHEMA {} TO ae_sql_reader').format(sql.Identifier(schema)))

    def execute(self, query, challenge, data, *, explain=False):
        tree=parse_submission(query,challenge.inputs)
        schema='attempt_'+uuid4().hex
        with self.connect() as db:
            self.load(db,schema,challenge.domain,data)
            db.commit()
            try:
                db.execute('SET TRANSACTION READ ONLY')
                db.execute("SET LOCAL temp_file_limit TO '16MB'")
                db.execute('SET LOCAL ROLE ae_sql_reader')
                db.execute(sql.SQL('SET LOCAL search_path TO {},pg_catalog').format(sql.Identifier(schema)))
                db.execute("SET LOCAL timezone TO 'UTC'")
                db.execute("SET LOCAL statement_timeout TO '2000ms'")
                db.execute("SET LOCAL lock_timeout TO '500ms'")
                db.execute("SET LOCAL work_mem TO '4MB'")
                if explain:
                    plan=db.execute('EXPLAIN (FORMAT JSON) '+query).fetchone()[0]
                    return {'plan':plan,'scope':'Actual local fixture plan; no production scale/timing claim.'}
                with db.cursor(name='bounded_answer') as cur:
                    cur.execute(query)
                    records=cur.fetchmany(201)
                    columns=[c.name for c in cur.description]
                if len(records)>200:raise SQLRejected('Output exceeds the 200-row fixture limit. Review the output grain.')
                if len(set(columns))!=len(columns):raise SQLRejected('Output columns need distinct names.')
                return {'columns':columns,'rows':[{k:value(v) for k,v in zip(columns,row)} for row in records],
                        'sources':sorted({t.name for t in tree.find_all(exp.Table) if t.name in challenge.inputs}),
                        'execution':'PostgreSQL; read-only ae_sql_reader; statement timeout 2 seconds'}
            finally:
                db.rollback()
                db.execute(sql.SQL('DROP SCHEMA {} CASCADE').format(sql.Identifier(schema)))
                db.commit()

    def initialize(self, domain, variant='clean', seed=1):
        if domain not in DOMAINS:raise ValueError('Unknown domain')
        schema='dataset_'+domain+'_'+uuid4().hex[:8]
        with self.connect() as db:self.load(db,schema,domain,fixture(domain,variant,seed),models=True)
        return {'schema':schema,'domain':domain,'variant':variant,'seed':seed,'models':len(DOMAINS[domain].tables),
                'usage':'Read-only fixture library. Reinitialize to create a separate reproducible snapshot.'}
