let token = '';
export class ApiError extends Error {
  constructor(message:string,public status:number){super(message);}
}
export async function initialize() {
  const config = await request<{request_token:string;sql_available:boolean}>('/config');
  token = config.request_token;
  return config;
}
export async function request<T>(path:string, method='GET', body?:unknown):Promise<T> {
  const response = await fetch('/api'+path,{method,headers:{'Content-Type':'application/json','X-Trainer-Token':token},body:body===undefined?undefined:JSON.stringify(body)});
  if(!response.ok) {
    const error = await response.json().catch(()=>({detail:'The application could not complete this request.'}));
    throw new ApiError(typeof error.detail==='string'?error.detail:'The request did not match the application contract.',response.status);
  }
  return response.json();
}
