export type * from "@data-observability/ui";
export type Answer={observed_failure:string;suspected_origin:string;grain:''|'one_row_per_order'|'one_row_per_item'|'unknown';affected_outputs:string[];fix_proposal:string;verification_plan:string;notes:string};
export type MapAction={sequence:number;kind:string;target:string|null;payload:Record<string,unknown>;created_at:string};
export type AssessmentResult={score:number;total:number;checks:{label:string;satisfied:boolean}[];independent:boolean;feedback:string;unassessed:string[];answer:Answer};
export type Investigation={id:string;system_id:string;snapshot_id:string;mode:'learning'|'assessment';status:'active'|'completed'|'abandoned';started_at:string;completed_at:string|null;independent:boolean;draft:Partial<Answer>;revision:number;result:AssessmentResult|null;actions:MapAction[];scenario:{id:string;title:string;brief:string};telemetry:{recorded_tests_inspected:number;tests_executed:number;verification_performed:boolean;time_to_relevant_evidence_seconds:number|null;note:string}};
export type HistoryRow={id:string;mode:string;status:string;started_at:string;result:AssessmentResult|null};
