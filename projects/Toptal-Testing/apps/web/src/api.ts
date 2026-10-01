import {createClient} from '@data-observability/ui';
export {ApiError} from '@data-observability/ui';
const client=createClient('X-Trainer-Token');
export const request=client.request;
export const initialize=async()=>await client.initialize() as {request_token:string;sql_available:boolean};
export const mapClient=client;
