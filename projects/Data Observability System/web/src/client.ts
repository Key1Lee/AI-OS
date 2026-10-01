export interface MapClient {
 initialize():Promise<{request_token:string;[key:string]:unknown}>;
 request<T>(path:string,method?:string,body?:unknown):Promise<T>;
}
export class ApiError extends Error {
 constructor(message:string,public status:number){super(message);}
}
export function createClient(tokenHeader='X-Observability-Token'):MapClient {
 let token='';
 async function request<T>(path:string, method='GET', body?:unknown):Promise<T> {
  const response = await fetch('/api'+path,{method,headers:{'Content-Type':'application/json',[tokenHeader]:token},body:body===undefined?undefined:JSON.stringify(body)});
  if(!response.ok) {
   const error = await response.json().catch(()=>({detail:'The application could not complete this request.'}));
   throw new ApiError(typeof error.detail==='string'?error.detail:'The request did not match the application contract.',response.status);
  }
  return response.json();
 }
 async function initialize(){const config=await request<{request_token:string;[key:string]:unknown}>('/config');token=config.request_token;return config;}
 return {initialize,request};
}
