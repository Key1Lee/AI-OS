"""Execute trusted synthetic transforms; export deterministic demo artifacts.

These are dbt-shaped demonstration fixtures, not output of a dbt command.
Uploaded artifacts/SQL are never passed to this generator.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import duckdb

DEMO_DIRECTORY = Path(__file__).resolve().parent / "commerce"
STAMP = '2026-10-02T00:00:00+00:00'
RUN = 'commerce-duckdb-demo-v1'


def generate() -> dict[str, dict]:
    connection = duckdb.connect(':memory:')
    try:
        connection.execute("CREATE TABLE raw_orders(order_id INTEGER, order_total DECIMAL(18,2))")
        connection.execute("INSERT INTO raw_orders VALUES (1,100),(2,50),(3,10)")
        connection.execute("CREATE TABLE raw_order_items(item_id INTEGER, order_id INTEGER, units INTEGER)")
        connection.execute("INSERT INTO raw_order_items VALUES (11,1,1),(12,1,2),(21,2,1),(31,3,1),(32,3,1)")
        specifications = [
            ('stg_orders','staging','1 row per order',['order_id'],['source.commerce.shopify.raw_orders'],'SELECT order_id,order_total FROM raw_orders',"SELECT order_id, order_total FROM {{ source('shopify','raw_orders') }}",'Standardizes order identifiers and preserves each order once.'),
            ('stg_order_items','staging','1 row per item',['item_id'],['source.commerce.shopify.raw_order_items'],'SELECT item_id,order_id,units FROM raw_order_items',"SELECT item_id, order_id, units FROM {{ source('shopify','raw_order_items') }}",'Keeps line items at their declared item grain.'),
            ('int_order_items','transformation','1 row per order',['order_id'],['model.commerce.stg_orders','model.commerce.stg_order_items'],'SELECT o.order_id,i.item_id,o.order_total FROM stg_orders o LEFT JOIN stg_order_items i ON o.order_id=i.order_id',"SELECT o.order_id,i.item_id,o.order_total FROM {{ ref('stg_orders') }} o LEFT JOIN {{ ref('stg_order_items') }} i ON o.order_id=i.order_id",'Combines order and item inputs for the order pipeline.'),
            ('fct_orders','transformation','1 row per order',['order_id'],['model.commerce.int_order_items'],'SELECT order_id,order_total AS revenue FROM int_order_items',"SELECT order_id,order_total AS revenue FROM {{ ref('int_order_items') }}",'Publishes the order-level fact used by finance.'),
            ('mart_revenue','mart','1 row per reporting day',['report_date'],['model.commerce.fct_orders'],"SELECT DATE '2026-10-01' AS report_date,SUM(revenue) AS total_revenue FROM fct_orders","SELECT DATE '2026-10-01' AS report_date,SUM(revenue) AS total_revenue FROM {{ ref('fct_orders') }}",'Summarizes daily revenue for business reporting.'),
        ]
        nodes, sources, catalog_nodes, catalog_sources, results = {}, {}, {}, {}, []
        source_specs = [('raw_orders','1 row per order',['order_id']),('raw_order_items','1 row per item',['item_id'])]
        for name,grain,keys in source_specs:
            key = 'source.commerce.shopify.'+name
            columns = {r[0]:{'name':r[0],'data_type':r[1],'description':None} for r in connection.execute('DESCRIBE '+name).fetchall()}
            sources[key] = {'unique_id':key,'resource_type':'source','name':name,'source_name':'shopify','schema':'raw','identifier':name,'description':'Synthetic Shopify commerce input.','columns':columns,'depends_on':{'nodes':[]},'meta':{'layer':'source','grain':grain,'primary_keys':keys,'source_system':'Shopify','owner':'Commerce data team'}}
            catalog_sources[key] = {'unique_id':key,'columns':{n:{'name':n,'type':c['data_type']} for n,c in columns.items()}}
        for name,layer,grain,keys,parents,sql,raw_code,description in specifications:
            connection.execute('CREATE TABLE '+name+' AS '+sql)
            key = 'model.commerce.'+name
            columns = {r[0]:{'name':r[0],'data_type':r[1],'description':None} for r in connection.execute('DESCRIBE '+name).fetchall()}
            meta = {'layer':layer,'grain':grain,'primary_keys':keys,'owner':'Analytics engineering'}
            if name in {'stg_orders','int_order_items','fct_orders'}:
                duplicates = connection.execute(f'SELECT COUNT(*) FROM (SELECT order_id FROM {name} GROUP BY order_id HAVING COUNT(*)>1)').fetchone()[0]
                meta['data_system_map'] = {'observations':[{'evidence_type':'duplicate_key_groups','expected':0,'actual':duplicates,'comparison_key':'order_id','observation_id':RUN}]}
            if name=='mart_revenue':
                expected = float(connection.execute('SELECT SUM(order_total) FROM raw_orders').fetchone()[0])
                actual = float(connection.execute('SELECT total_revenue FROM mart_revenue').fetchone()[0])
                meta['data_system_map'] = {'observations':[{'evidence_type':'reconciled_revenue','expected':expected,'actual':actual,'comparison_key':'2026-10-01','observation_id':RUN}]}
            nodes[key] = {'unique_id':key,'resource_type':'model','name':name,'schema':'analytics','description':description,'columns':columns,'depends_on':{'nodes':parents},'meta':meta,'config':{'materialized':'table'},'raw_code':raw_code,'compiled_code':sql}
            catalog_nodes[key] = {'unique_id':key,'columns':{n:{'name':n,'type':c['data_type']} for n,c in columns.items()}}
            results.append({'unique_id':key,'status':'success','execution_time':None,'message':'Trusted synthetic DuckDB transform completed.','timing':[{'name':'execute','started_at':STAMP,'completed_at':STAMP}]})
        for name in ['stg_orders','fct_orders']:
            key = 'test.commerce.unique_'+name+'_order_id'
            parent = 'model.commerce.'+name
            count = connection.execute(f'SELECT COUNT(*) FROM (SELECT order_id FROM {name} GROUP BY order_id HAVING COUNT(*)>1)').fetchone()[0]
            nodes[key] = {'unique_id':key,'resource_type':'test','name':'unique('+name+'.order_id)','attached_node':parent,'depends_on':{'nodes':[parent]},'columns':{},'config':{'severity':'ERROR'},'test_metadata':{'name':'unique','kwargs':{'column_name':'order_id'}},'raw_code':f'SELECT order_id,COUNT(*) FROM {name} GROUP BY order_id HAVING COUNT(*)>1'}
            results.append({'unique_id':key,'status':'fail' if count else 'pass','failures':count,'message':f'{count} duplicate order_id groups observed in the synthetic DuckDB fixture.','execution_time':None,'timing':[{'name':'execute','started_at':STAMP,'completed_at':STAMP}]})
        outputs = {'exposure.commerce.executive_dashboard':{'unique_id':'exposure.commerce.executive_dashboard','resource_type':'exposure','name':'Executive Dashboard','description':'Executives use this report to review daily revenue.','depends_on':{'nodes':['model.commerce.mart_revenue']},'columns':{},'meta':{'layer':'output','owner':'Finance'}}}
        metrics = {'metric.commerce.daily_revenue':{'unique_id':'metric.commerce.daily_revenue','resource_type':'metric','name':'Daily Revenue','description':'Reported sum of order revenue for the reporting date.','depends_on':{'nodes':['model.commerce.mart_revenue']},'columns':{},'meta':{'layer':'output','grain':'1 value per reporting day'}}}
        metadata = {'generated_at':STAMP,'invocation_id':RUN,'sample':True,'producer':'Original trusted DuckDB fixture generator; no dbt command was run.'}
        manifest = {'metadata':{**metadata,'dbt_schema_version':'https://schemas.getdbt.com/dbt/manifest/v12.json'},'nodes':nodes,'sources':sources,'exposures':outputs,'metrics':metrics}
        manifest['parent_map'] = {key:raw['depends_on']['nodes'] for group in [nodes,sources,outputs,metrics] for key,raw in group.items()}
        freshness = {'metadata':{**metadata,'dbt_schema_version':'https://schemas.getdbt.com/dbt/sources/v3.json'},'results':[{'unique_id':key,'status':'pass','snapshotted_at':STAMP} for key in sources]}
        return {'manifest.json':manifest,'run_results.json':{'metadata':{**metadata,'dbt_schema_version':'https://schemas.getdbt.com/dbt/run-results/v6.json'},'args':{'which':'build'},'results':results},'catalog.json':{'metadata':{**metadata,'dbt_schema_version':'https://schemas.getdbt.com/dbt/catalog/v1.json'},'nodes':catalog_nodes,'sources':catalog_sources},'sources.json':freshness}
    finally:
        connection.close()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check',action='store_true',help='Compare trusted execution with checked-in fixtures without changing files.')
    args = parser.parse_args()
    destination = DEMO_DIRECTORY
    if not args.check:
        destination.mkdir(parents=True,exist_ok=True)
    for name,body in generate().items():
        encoded = json.dumps(body,indent=2,sort_keys=True,allow_nan=False)+'\n'
        path = destination/name
        if args.check:
            if not path.exists() or path.read_text()!=encoded:
                raise SystemExit('Demonstration fixture differs: '+name)
        else:
            path.write_text(encoded)
    print('Commerce fixture execution verified.' if args.check else 'Original commerce demonstration artifacts written.')


if __name__=='__main__':
    main()
