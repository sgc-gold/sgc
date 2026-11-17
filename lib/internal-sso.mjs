import {createSsoClient,APP_COOKIE} from './sgc-sso-client.mjs';
export const ORIGIN='https://sgc-internal-portal.pages.dev';
const AUTH='https://sgc-auth.sgc-gold.workers.dev';
const safe={'cache-control':'private, no-store, max-age=0','pragma':'no-cache','referrer-policy':'same-origin','x-content-type-options':'nosniff'};
const text=(body,status)=>new Response(body,{status,headers:{...safe,'content-type':'text/plain; charset=utf-8'}});
const page=(title,body)=>new Response(`<!doctype html><html lang="ja"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>${title} | SGC 社内ポータル</title><h1>${title}</h1>${body}</html>`,{headers:{...safe,'content-type':'text/html; charset=utf-8','content-security-policy':"default-src 'none'; form-action 'self'; frame-ancestors 'none'; base-uri 'none'"}});
const denied=request=>{
  const url=new URL(request.url);
  const html=url.pathname==='/'||url.pathname.endsWith('.html')||['document','iframe'].includes(request.headers.get('sec-fetch-dest'))||request.headers.get('accept')?.includes('text/html');
  if(request.method!=='GET'||url.pathname.startsWith('/api/')||url.pathname.startsWith('/data/')||!html)
    return Response.json({error:'LOGIN_REQUIRED'},{status:401,headers:safe});
  return new Response(null,{status:303,headers:{...safe,location:'/auth/login?return='+encodeURIComponent(url.pathname+url.search)}});
};
function hasAppCookie(request){return (request.headers.get('cookie')??'').split(';').some(v=>v.trim().startsWith(APP_COOKIE+'='));}
function appToken(request){const values=(request.headers.get('cookie')??'').split(';').map(s=>s.trim()).filter(s=>s.startsWith(APP_COOKIE+'='));return values.length===1?values[0].slice(APP_COOKIE.length+1):'';}
async function protectedResponse(context){
  const result=await context.next(),h=new Headers(result.headers);
  for(const [k,v] of Object.entries(safe))h.set(k,v);
  return new Response(result.body,{status:result.status,statusText:result.statusText,headers:h});
}
const blocked=p=>['/scripts','/.github','/gas','/tools','/lib','/functions'].some(x=>p===x||p.startsWith(x+'/'))||['/data/diamonds.json','/package.json','/package-lock.json','/wrangler.toml','/wrangler.jsonc','/.env'].includes(p);
export function createInternalMiddleware() {
  return async context=>{
    const {request,env}=context,url=new URL(request.url);
    if(url.origin!==ORIGIN)return text('Not found',404); // Preview aliases must not serve protected content.
    if(blocked(url.pathname))return text('Not found',404);
    // The non-caching SW must update even after a session expires. Contains no business data.
    if(url.pathname==='/sw.js'&&['GET','HEAD'].includes(request.method)){
      const result=await context.next();const h=new Headers(result.headers);
      for(const [k,v] of Object.entries(safe))h.set(k,v);
      return new Response(result.body,{status:result.status,headers:h});
    }
    if(url.pathname==='/auth/signed-out'&&request.method==='GET')return page('ログアウトしました','<p>SGC共通セッションを終了しました。</p><a href="/auth/login">LINE WORKSでログイン</a>');
    try {
      if(env.INTERNAL_PORTAL_SSO_MODE!=='required')return text('認証設定を確認できません。',503);
      if(!env.SGC_AUTH?.admit)return text('認証設定を確認できません。',503);
      if(await env.SGC_AUTH.admit(request.headers.get('cf-connecting-ip'),appToken(request))!==true)return text('しばらくしてからお試しください。',429);
      const sso=createSsoClient({origin:ORIGIN,authOrigin:AUTH,appId:'internal-portal',binding:env.SGC_AUTH});
      const auth=await sso.handle(request);if(auth)return auth;
      if(url.pathname==='/auth/logout'&&request.method==='GET')return page('ログアウトの確認','<p>SGC共通セッションを終了します。</p><form method="post" action="/auth/logout"><button type="submit">ログアウト</button></form>');
      if(url.pathname.startsWith('/auth/'))return text('Not found',404);
      let allowed=false;
      // A present shared cookie is always checked strictly, including empty/duplicate/broken cookies.
      if(hasAppCookie(request))allowed=!!await sso.principal(request);
      if(!allowed)return denied(request);
      return protectedResponse(context);
    }catch{return text('ログイン状態を確認できません。しばらくしてから再度お試しください。',503);}
  };
}
