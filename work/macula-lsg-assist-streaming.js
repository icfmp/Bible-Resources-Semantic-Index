// Streaming holdout-only evidence counter. No source text is retained in receipts.
(function streaming(){
 const key=x=>JSON.stringify(x), norm=s=>s.normalize("NFD").replace(/[\u0591-\u05af\u05bd]/gu,"").normalize("NFC");
 const ft=s=>Array.from(s.matchAll(/[\p{L}\p{N}\p{M}]+(?:['’-][\p{L}\p{N}\p{M}]+)*/gu),m=>({word:m[0].toLowerCase().replace(/’/g,"'").normalize("NFC"),start:Array.from(s.slice(0,m.index)).length,end:Array.from(s.slice(0,m.index+m[0].length)).length}));
 const hk=w=>key([norm(w[2]),w[3],w[4],w[5],w[6]]);
 const general=s=>{let [surface,lemma,pos,morph,lang]=JSON.parse(s);return key([lemma,pos,morph?.slice(0,2),lang])};
 const content=s=>["noun","verb","adjective","adverb"].includes(JSON.parse(s)[2]);
 const stop=new Set("a à au aux ce ces cet cette de des du en et il ils je la le les leur leurs lui ma mais me mes mon ne ni nos notre nous on ou par pas pour qu que qui sa se ses si son sur ta te tes toi ton tu un une vos votre vous y est sont était étaient être avoir ont avait tout tous toute toutes".split(" "));
 function prepare(c,requireGold=true){
  if(requireGold){
 const chapter=Number(c.scope.split(".").at(-1)),m=c.g?.sources?.macula,segments=m?.segments??[];
 const own=segments.filter(s=>s.native_chapter===chapter);
 if(c.g?.editorial_review?.passes!==2||(!own.length?m?.blob!==c.h.git_blob:!own.every(s=>s.blob===c.h.git_blob))||c.g.sources.lsg.chapter_prose_sha256!==c.f.reading_text_sha256)throw Error("Missing audited ledger or source lock mismatch "+c.scope);
}
  const groups=new Map(),ids=new Map(),french=new Map(Object.entries(c.f.verses).map(([v,s])=>[+v,ft(s)]));
  for(const w of c.h.words){let v=+w[1].split("!")[0].split(":").at(-1),a=groups.get(v)??[];if(ids.has(w[0]))throw Error("Duplicate source ID "+c.scope);ids.set(w[0],{v,i:a.length,w});a.push(w);groups.set(v,a)}
  return{groups,ids,french};
 }
 const hits=(arr,sub)=>{let o=[];for(let i=0;i+sub.length<=arr.length;i++)if(sub.every((x,j)=>x===arr[i+j]))o.push(i);return o};
 function queries(held){
  const q=new Map(),byId=[],verseRows=[];
  function add(tier,seq,occ){let k=key([tier,seq]);let e=q.get(k);if(!e){e={id:byId.length,occ:[]};q.set(k,e);byId.push(e)}e.occ.push(occ)}
  for(let ci=0;ci<held.length;ci++){const c=held[ci],p=prepare(c,false);if(p.groups.size!==p.french.size||[...p.groups.keys()].some(v=>!p.french.has(v)))throw Error("Heldout needs explicit verse mapping "+c.scope);
   for(const [v,words] of p.groups){let hs=words.map(hk),ls=hs.map(general),fs=p.french.get(v).map(x=>x.word);verseRows.push({ci,v});
    for(let i=0;i<hs.length;i++)for(let n=1;n<=Math.min(5,hs.length-i);n++){
     let seq=hs.slice(i,i+n);
     for(const [tier,src,pattern] of [[2,hs,seq],...(n===1&&content(seq[0])?[[1,ls,[ls[i]]]]:[])]){
      if(hits(src,pattern).length!==1)continue;
      add(tier,pattern,{ci,v,i,n,fs,lexical:n===1&&content(seq[0]),tier});
     }
    }
   }
  }return{q,byId,verseRows,held};
 }
 function scan(c,qs){
  const p=prepare(c),seen=new Set(),denom={},candidates={},skipped={nonContiguous:0,otherVerse:0,unknownOriginal:0};
  for(const rel of c.g.relations){if(rel.kind!=="translation")continue;let hs=rel.hebrew.map(id=>p.ids.get(id));
   if(!hs.length||hs.some(x=>!x)){
 const chapter=Number(c.scope.split(".").at(-1)),prefix=c.h.words[0]?.[0]?.slice(0,3);
 const unknown=rel.hebrew.filter(id=>!p.ids.has(id));
 const segments=(c.g.sources.macula.segments??[]).filter(s=>s.native_chapter!==chapter);
 // Declared foreign segments are excluded from this same-native-verse experiment,
 // not accepted as validated source IDs. All unknown IDs must be covered by an
 // explicit foreign segment and all French targets must belong to that segment.
 const declared=unknown.length&&unknown.every(id=>{
  if(typeof id!=="string"||!id.startsWith(prefix)||!/^o\d{11,}/.test(id))return false;
  const nc=Number(id.slice(3,6)),nv=Number(id.slice(6,9));
  return segments.some(s=>s.blob&&s.native_chapter===nc&&nv>=s.native_first&&nv<=s.native_last&&rel.french.every(t=>t[0]>=s.lsg_first&&t[0]<=s.lsg_last));
 });
 if(declared){skipped.unknownOriginal++;continue;}
 throw Error("Unknown original ID "+c.scope+" "+unknown.join(","));
}
   hs.sort((a,b)=>a.i-b.i);let vs=hs[0].v;
   if(hs.some((x,i)=>x.v!==vs||x.i!==hs[0].i+i)){skipped.nonContiguous++;continue;}
   let fs=rel.french.slice().sort((a,b)=>a[1]-b[1]);
   if(!fs.length||fs.some((x,i)=>x[0]!==vs||x[1]!==fs[0][1]+i)){skipped.otherVerse++;continue;}
   const tokens=p.french.get(vs);
   if(fs.some(t=>!tokens?.[t[1]-1]||tokens[t[1]-1].start!==t[2]||tokens[t[1]-1].end!==t[3]))throw Error("French offset mismatch "+c.scope+"."+vs);
   const h=hs.map(x=>hk(x.w)),f=fs.map(t=>tokens[t[1]-1].word);
   for(const [tier,seq] of [[2,h],...(h.length===1&&content(h[0])?[[1,h.map(general)]]:[])]){
    const query=qs.q.get(key([tier,seq]));if(!query)continue;
    let sig=key([query.id,f,vs]);if(seen.has(sig))continue;seen.add(sig);denom[query.id]=(denom[query.id]??0)+1;
    for(const o of query.occ){let found=hits(o.fs,f);if(found.length!==1)continue;
     let j=found[0],id=[o.ci,o.v,o.i,o.n,j,f.length,o.tier].join("."),single=o.lexical&&f.length===1&&!stop.has(f[0])?1:0;
     let old=candidates[id]??[query.id,0,1,single];if(old[0]!==query.id||old[3]!==single)throw Error("Candidate key conflict");
     old[1]++;candidates[id]=old;
    }
   }
  }return{scope:c.scope,denom,candidates,skipped,locks:c.locks};
 }
 function merge(a,b){
  for(const [k,v] of Object.entries(b.denom))a.denom[k]=(a.denom[k]??0)+v;
  for(const [id,v] of Object.entries(b.candidates)){let old=a.candidates[id];if(!old){a.candidates[id]=v.slice();continue;}if(old[0]!==v[0]||old[3]!==v[3])throw Error("Candidate key conflict "+id);old[1]+=v[1];old[2]+=v[2];}
  return a;
 }
 function predictions(qs,a,opts){
  let byVerse=new Map();
  for(const [id,[qid,support,chapters,single]] of Object.entries(a.candidates)){let [ci,v,i,n,j,m,tier]=id.split(".").map(Number),ratio=support/a.denom[qid];
   if(!Number.isFinite(ratio)||ratio>1)throw Error("Invalid support ratio");
   if(support<(opts.reviewMin??1))continue;
   let h=Array.from({length:n},(_,k)=>i+k+1),f=Array.from({length:m},(_,k)=>j+k+1),strong=single&&support>=(opts.minSupport??3)&&chapters>=(opts.minChapters??2)&&ratio>=(opts.minDominance??0.6)&&(tier===2||opts.allowLemmaStrong===true);
   let c={h,f,tier,support,chapters,ratio,strong,score:(strong?1000000:0)+tier*100000+Math.round(ratio*1000)*10+Math.min(support,999)},vk=ci+"."+v,all=byVerse.get(vk)??new Map(),k=key([h,f]),old=all.get(k);
   if(!old||c.score>old.score)all.set(k,c);byVerse.set(vk,all);
  }
  const outputs=qs.held.map(c=>({scope:c.scope,status:"all_proposals_unreviewed",rows:[]}));
  for(const {ci,v} of qs.verseRows){const all=byVerse.get(ci+"."+v)??new Map(),list=[...all.values()].sort((a,b)=>b.score-a.score),selected=[],usedH=new Set(),usedF=new Set();
   const overlap=(a,b)=>a.h.some(x=>b.h.includes(x))||a.f.some(x=>b.f.includes(x));
   for(const a of list.filter(x=>x.strong)){if(a.h.some(x=>usedH.has(x))||a.f.some(x=>usedF.has(x)))continue;if(list.some(b=>b!==a&&b.strong&&b.score>=a.score&&overlap(a,b)))continue;selected.push(a);a.h.forEach(x=>usedH.add(x));a.f.forEach(x=>usedF.add(x))}
   const succinct=a=>({h:a.h,f:a.f,tier:a.tier===2?"exact":"lemma",support:a.support,chapters:a.chapters,dominance:Math.round(a.ratio*1000)/1000,status:"proposal_pending_editorial_review"});
   outputs[ci].rows.push({nativeVerse:v,frenchVerse:v,prefill:selected.map(succinct),review:list.filter(a=>!selected.includes(a)).map(succinct)});
  }return outputs;
 }
 return{queries,scan,merge,predictions,prepare};
})()
