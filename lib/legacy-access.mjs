// Transition only: independently verify the old Access assertion, never use its email
// to enroll a LINE WORKS identity. Required SSO mode never calls this verifier.
let cached;
const decode=s=>{
  if(!/^[A-Za-z0-9_-]+$/.test(s))throw Error('JWT_INVALID');
  return Uint8Array.from(atob(s.replace(/-/g,'+').replace(/_/g,'/')),c=>c.charCodeAt(0));
};
export async function verifyLegacyAccess(request,env,{fetchKeys=fetch,now=Math.floor(Date.now()/1000)}={}){
  const issuer=env.LEGACY_ACCESS_ISSUER,aud=env.LEGACY_ACCESS_AUD;
  if(typeof issuer!=='string'||!/^https:\/\/[a-z0-9-]+\.cloudflareaccess\.com$/.test(issuer)||typeof aud!=='string'||! /^[a-f0-9]{64}$/.test(aud))return false;
  const token=request.headers.get('cf-access-jwt-assertion');
  if(!token||token.length>16384)return false;
  try {
    const parts=token.split('.');if(parts.length!==3)return false;
    const header=JSON.parse(new TextDecoder().decode(decode(parts[0]))),claim=JSON.parse(new TextDecoder().decode(decode(parts[1])));
    if(header.alg!=='RS256'||typeof header.kid!=='string'||header.kid.length>256||header.crit||claim.iss!==issuer||!Array.isArray(claim.aud)||!claim.aud.includes(aud)||
      !Number.isSafeInteger(claim.exp)||claim.exp<=now||!Number.isSafeInteger(claim.iat)||claim.iat>now+60||claim.nbf!==undefined&&(!Number.isSafeInteger(claim.nbf)||claim.nbf>now+60))return false;
    if(!cached||cached.issuer!==issuer||cached.until<=now||!cached.keys.some(k=>k.kid===header.kid)){
      const response=await fetchKeys(issuer+'/cdn-cgi/access/certs',{redirect:'error'});
      if(!response.ok)throw Error('ACCESS_KEYS_UNAVAILABLE');
      const set=await response.json();if(!Array.isArray(set.keys)||set.keys.length>16)throw Error('ACCESS_KEYS_INVALID');
      cached={issuer,until:now+300,keys:set.keys};
    }
    const keys=cached.keys.filter(k=>k.kid===header.kid&&k.kty==='RSA'&&(!k.alg||k.alg==='RS256')&&(!k.use||k.use==='sig'));
    if(keys.length!==1)return false;
    const key=await crypto.subtle.importKey('jwk',keys[0],{name:'RSASSA-PKCS1-v1_5',hash:'SHA-256'},false,['verify']);
    return crypto.subtle.verify('RSASSA-PKCS1-v1_5',key,decode(parts[2]),new TextEncoder().encode(parts[0]+'.'+parts[1]));
  }catch{return false;}
}
