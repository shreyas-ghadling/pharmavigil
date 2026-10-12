export class ApiError extends Error {
  status:number;
  constructor(status:number,message:string){super(message);this.status=status;}
}
let csrf = '';
export function setCsrf(value:string){csrf=value;}
export async function api<T>(path:string, options:RequestInit={}):Promise<T>{
  const headers = new Headers(options.headers);
  if(options.body && !(options.body instanceof FormData))headers.set('Content-Type','application/json');
  if(options.method && options.method !== 'GET') headers.set('X-CSRF-Token',csrf);
  const response = await fetch(`/api${path}`,{...options,headers,credentials:'same-origin'});
  if(!response.ok){
    if(response.status===401 && !path.startsWith('/auth/'))window.dispatchEvent(new Event('pharmavigil-session-expired'));
    const data = await response.json().catch(()=>({message:'Unable to reach the server.'}));
    const details = (data.fields || []).map((f:{field:string;message:string})=>`${f.field}: ${f.message}`);
    throw new ApiError(response.status,[data.message,...details,...(data.errors || [])].filter(Boolean).join('\n'));
  }
  return response.json();
}
export async function download(path:string,filename:string){
  const response = await fetch(`/api${path}`,{credentials:'same-origin'});
  if(!response.ok){const e = await response.json();throw new Error(e.message);}
  const url = URL.createObjectURL(await response.blob());
  const anchor = document.createElement('a');anchor.href=url;anchor.download=filename;anchor.click();
  setTimeout(()=>URL.revokeObjectURL(url),1000);
}
