"""CLI for the reusable learning framework; original lab CLI remains available."""
import argparse
import json
import os
from pathlib import Path
import sys
from .adapters.bridge import ROOT
from .learning_engine import LearningEngine
from .problems import PROBLEMS, VERSION
from .store import Store, StateError
from .sql_lab.integrations import orchestrate, semantic_reference
from .sql_lab.postgres import Postgres
from .sql_lab.datasets import DOMAINS


def dump(value):print(json.dumps(value,indent=2))

def main(argv=None):
    parser=argparse.ArgumentParser(description='AE Lab curriculum and adaptive learning')
    parser.add_argument('--state-dir',type=Path,default=Path(os.environ.get('AE_LAB_STATE_DIR',ROOT/'.lab')))
    sub=parser.add_subparsers(dest='command',required=True)
    item=sub.add_parser('catalog');item.add_argument('--mode',default='LEARN');item.add_argument('--focus',choices=['all','sql','reasoning'],default='all')
    item=sub.add_parser('start');item.add_argument('problem_id');item.add_argument('--mode',default='LEARN')
    item=sub.add_parser('view');item.add_argument('run_id')
    item=sub.add_parser('act');item.add_argument('run_id');item.add_argument('action');item.add_argument('--answer-file',type=Path)
    item=sub.add_parser('recommend');item.add_argument('--mode',default='LEARN');item.add_argument('--focus',choices=['all','sql','reasoning'],default='all')
    item=sub.add_parser('coverage');item.add_argument('--output',type=Path)
    item=sub.add_parser('recall');item.add_argument('problem_id');item.add_argument('--concept')
    item=sub.add_parser('review');item.add_argument('run_id');item.add_argument('attempt_id');item.add_argument('--review-file',type=Path,required=True)
    item=sub.add_parser('respond');item.add_argument('run_id');item.add_argument('question_id');item.add_argument('--response-file',type=Path,required=True)
    item=sub.add_parser('integrations');item.add_argument('--domain',choices=['fintech','ecommerce','saas'],default='fintech')
    item=sub.add_parser('init-dataset');item.add_argument('domain',choices=sorted(DOMAINS));item.add_argument('--variant',choices=['clean','adversarial','recall'],default='clean')
    item=sub.add_parser('evidence');item.add_argument('run_id',help='Tutor/developer-only full local evidence, including assessed tests')
    args=parser.parse_args(argv)
    try:
        engine=LearningEngine(Store(args.state_dir))
        if args.command=='catalog':dump(engine.catalog(args.mode,args.focus))
        elif args.command=='start':dump(engine.view(engine.start(args.problem_id,args.mode)))
        elif args.command=='view':dump(engine.view(engine.store.get(args.run_id)))
        elif args.command=='act':
            answer=json.loads(args.answer_file.read_text()) if args.answer_file else {}
            dump(engine.view(engine.action(engine.store.get(args.run_id),args.action,answer)))
        elif args.command=='recommend':dump(engine.recommend(args.mode,args.focus))
        elif args.command=='coverage':
            matrix=engine.mastery.coverage(PROBLEMS)
            if args.output:
                args.output.parent.mkdir(parents=True,exist_ok=True);args.output.write_text(json.dumps(matrix,indent=2)+'\n')
            dump(matrix)
        elif args.command=='recall':dump(engine.view(engine.start_recall(args.problem_id,args.concept)))
        elif args.command=='review':
            review=json.loads(args.review_file.read_text());dump(engine.view(engine.review(args.run_id,args.attempt_id,**review)))
        elif args.command=='respond':
            response=json.loads(args.response_file.read_text());dump(engine.view(engine.respond_to_question(args.run_id,args.question_id,**response)))
        elif args.command=='evidence':dump(engine.store.get(args.run_id))
        elif args.command=='init-dataset':dump(engine.postgres.initialize(args.domain,args.variant))
        elif args.command=='integrations':
            from uuid import uuid4
            dump({'postgres':engine.postgres.health(),'semantic_reference':semantic_reference(),
                  'orchestration':orchestrate(str(uuid4()),10),'scope':'Read-only semantic reference and native virtual replay. No production connection or actual orchestrated job claimed.'})
        return 0
    except (ValueError,StateError,RuntimeError,OSError) as exc:
        print(str(exc),file=sys.stderr);return 1

if __name__=='__main__':raise SystemExit(main())
