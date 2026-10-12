import { createContext, useContext, useEffect, type ReactNode } from 'react';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { api, ApiError, setCsrf } from './api';
import type { User } from './types';
interface Auth {user:User|null;loading:boolean;error:Error|null;refresh:()=>void;login:(username:string,password:string)=>Promise<void>;logout:()=>Promise<void>}
const AuthContext=createContext<Auth|null>(null);
export function AuthProvider({children}:{children:ReactNode}){
  const cache=useQueryClient();
  useEffect(()=>{const expired=()=>{void cache.cancelQueries().then(()=>{setCsrf('');cache.setQueryData(['session'],null);cache.removeQueries({predicate:q=>q.queryKey[0]!=='session'});});};window.addEventListener('pharmavigil-session-expired',expired);return()=>window.removeEventListener('pharmavigil-session-expired',expired);},[cache]);
  const query=useQuery<User|null>({queryKey:['session'],queryFn:async()=>{
    try{const u=await api<User>('/auth/me');setCsrf(u.csrf);return u;}
    catch(e){if(e instanceof ApiError && e.status===401){setCsrf('');return null;}throw e;}
  },retry:false,refetchInterval:300000});
  async function login(username:string,password:string){
    const u=await api<User>('/auth/login',{method:'POST',body:JSON.stringify({username,password})});
    await cache.cancelQueries({queryKey:['session']});
    cache.removeQueries({predicate:q=>q.queryKey[0]!=='session'});setCsrf(u.csrf);cache.setQueryData(['session'],u);
  }
  async function logout(){await api('/auth/logout',{method:'POST'});await cache.cancelQueries();setCsrf('');cache.setQueryData(['session'],null);cache.removeQueries({predicate:q=>q.queryKey[0]!=='session'});}
  return <AuthContext.Provider value={{user:query.data??null,loading:query.isPending,error:query.error,refresh:()=>{void query.refetch();},login,logout}}>{children}</AuthContext.Provider>;
}
export function useAuth(){const value=useContext(AuthContext);if(!value)throw new Error('Auth provider is missing');return value;}
