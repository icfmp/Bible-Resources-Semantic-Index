// Research prototype; evaluate this expression to obtain the API. No source text persisted.
(function engine(){
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
 function buildEvidence(chapters,seed=null){
  const exact=new Map(),lemma=new Map(),scopes=new Set(),skipped={foreignSegment:0,nonContiguous:0,otherVerse:0};
  function add(h,f,refs){
   if(!h.length||!f.length)return;
   for(const [idx,hs] of [[exact,h],...(h.length===1&&content(h[0])?[[lemma,h.map(general)]]:[])]){
    let k=key(hs),bucket=idx.get(k)??new Map(),fk=key(f),e=bucket.get(fk)??{f,refs:new Set()};
    for(const ref of refs){e.refs.add(ref);scopes.add(ref.split(".").slice(0,2).join("."))}bucket.set(fk,e);idx.set(k,bucket)
   }
  }
  if(seed)for(const e of seed.entries)add(e.h,e.f.map(s=>s.toLowerCase().replace(/’/g,"'").normalize("NFC")),e.examples);
  for(const c of chapters){if(scopes.has(c.scope))throw Error("Repeated training chapter "+c.scope);let p=prepare(c);scopes.add(c.scope);for(const rel of c.g.relations){if(rel.kind!=="translation")continue;let hs=rel.hebrew.map(id=>p.ids.get(id));if(!hs.length||hs.some(x=>!x)){
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
 if(declared){skipped.foreignSegment++;continue;}
 throw Error("Unknown original ID "+c.scope+" "+unknown.join(","));
}hs.sort((a,b)=>a.i-b.i);let vs=hs[0].v;if(hs.some((x,i)=>x.v!==vs||x.i!==hs[0].i+i)){skipped.nonContiguous++;continue;}let fs=rel.french.slice().sort((a,b)=>a[1]-b[1]);if(!fs.length||fs.some((x,i)=>x[0]!==vs||x[1]!==fs[0][1]+i)){skipped.otherVerse++;continue;}const tokens=p.french.get(vs);if(fs.some(t=>!tokens?.[t[1]-1]||tokens[t[1]-1].start!==t[2]||tokens[t[1]-1].end!==t[3]))throw Error("French offset mismatch "+c.scope);add(hs.map(x=>hk(x.w)),fs.map(t=>tokens[t[1]-1].word),[`${c.scope}.${vs}`]);}}
  return{exact,lemma,scopes,skipped};
 }
 const hits=(arr,sub)=>{let o=[];for(let i=0;i+sub.length<=arr.length;i++)if(sub.every((x,j)=>x===arr[i+j]))o.push(i);return o};
 const chapterSupport=e=>new Set([...e.refs].map(s=>s.split(".").slice(0,2).join("."))).size;
 const dominance=(e,b)=>e.refs.size/[...b.values()].reduce((a,z)=>a+z.refs.size,0);
 function propose(c,bank,opts={},verseMap={}){
  if(bank.scopes.has(c.scope))throw Error("Training chapter cannot be evaluated/predicted as unseen "+c.scope);
  const p=prepare(c,false),out=[];
  // Caller must explicitly resolve differences in native/French versification.
  const nativeVerses=[...p.groups.keys()], frenchVerses=[...p.french.keys()];
  if(!Object.keys(verseMap).length&&(nativeVerses.length!==frenchVerses.length||nativeVerses.some(v=>!p.french.has(v))))throw Error("Explicit versification required "+c.scope);
  for(const [v,words] of p.groups){const fv=verseMap[v]??v;if(!Number.isInteger(fv)||!p.french.has(fv)){out.push({nativeVerse:v,status:"explicit_versification_required",prefill:[],review:[]});continue}
   let hs=words.map(hk),ls=hs.map(general),fs=p.french.get(fv).map(x=>x.word),all=new Map();
   for(let i=0;i<hs.length;i++)for(let n=1;n<=Math.min(5,hs.length-i);n++){
    let seq=hs.slice(i,i+n);
    for(const [tier,idx,src,pattern] of [[2,bank.exact,hs,seq],...(n===1&&content(seq[0])?[[1,bank.lemma,ls,[ls[i]]]]:[])]){
     let bucket=idx.get(key(pattern));if(!bucket||hits(src,pattern).length!==1)continue;
     for(const e of bucket.values()){
      let support=e.refs.size;if(support<(opts.reviewMin??1))continue;let found=hits(fs,e.f);if(found.length!==1)continue;
      let j=found[0],h=Array.from({length:n},(_,k)=>i+k+1),f=e.f.map((_,k)=>j+k+1),chapters=chapterSupport(e),ratio=dominance(e,bucket),single=n===1&&e.f.length===1&&content(seq[0])&&!stop.has(e.f[0]),strong=single&&support>=(opts.minSupport??3)&&chapters>=(opts.minChapters??2)&&ratio>=(opts.minDominance??0.6)&&(tier===2||opts.allowLemmaStrong===true);
      let c={h,f,tier,support,chapters,ratio,strong,score:(strong?1000000:0)+tier*100000+Math.round(ratio*1000)*10+Math.min(support,999)},k=key([h,f]),old=all.get(k);
      if(!old||c.score>old.score)all.set(k,c);
     }
    }
   }
   const list=[...all.values()].sort((a,b)=>b.score-a.score),selected=[],usedH=new Set(),usedF=new Set();
   const overlap=(a,b)=>a.h.some(x=>b.h.includes(x))||a.f.some(x=>b.f.includes(x));
   for(const a of list.filter(x=>x.strong)){if(a.h.some(x=>usedH.has(x))||a.f.some(x=>usedF.has(x)))continue;if(list.some(b=>b!==a&&b.strong&&b.score>=a.score&&overlap(a,b)))continue;selected.push(a);a.h.forEach(x=>usedH.add(x));a.f.forEach(x=>usedF.add(x))}
   const succinct=a=>({h:a.h,f:a.f,tier:a.tier===2?"exact":"lemma",support:a.support,chapters:a.chapters,dominance:Math.round(a.ratio*1000)/1000,status:"proposal_pending_editorial_review"});
   out.push({nativeVerse:v,frenchVerse:fv,prefill:selected.map(succinct),review:list.filter(a=>!selected.includes(a)).map(succinct),unfilledH:hs.map((_,i)=>i+1).filter(i=>!usedH.has(i)),unfilledF:fs.map((_,i)=>i+1).filter(i=>!usedF.has(i))});
  }return{scope:c.scope,status:"all_proposals_unreviewed",rows:out};
 }
 function score(c,pred){
  const p=prepare(c),gold=new Set(),pairs=new Set(),hgold=new Set(),fgold=new Set();for(const r of c.g.relations.filter(x=>x.kind==="translation")){let hs=r.hebrew.slice().sort(),fs=r.french.map(t=>`${t[0]}.${t[1]}`).sort();gold.add(key([hs,fs]));for(const h of hs){hgold.add(h);for(const f of fs){pairs.add(key([h,f]));fgold.add(f)}}}
  let proposals=0,exact=0,correctPairs=0,totalPairs=0,reviewAlternatives=0,oracle=new Set(),hseen=new Set(),fseen=new Set();
  for(const row of pred.rows){let words=p.groups.get(row.nativeVerse);for(const a of [...row.prefill,...row.review]){const hs=a.h.map(i=>words[i-1][0]).sort(),fs=a.f.map(i=>`${row.frenchVerse}.${i}`).sort();if(gold.has(key([hs,fs])))oracle.add(key([hs,fs]))}
   reviewAlternatives+=row.review.length;for(const a of row.prefill){let hs=a.h.map(i=>words[i-1][0]).sort(),fs=a.f.map(i=>`${row.frenchVerse}.${i}`).sort();proposals++;if(gold.has(key([hs,fs])))exact++;for(const h of hs){hseen.add(h);for(const f of fs){fseen.add(f);totalPairs++;if(pairs.has(key([h,f])))correctPairs++}}}
  }return{scope:c.scope,verses:pred.rows.length,goldRelations:gold.size,goldPairs:pairs.size,proposals,exact,correctPairs,totalPairs,reviewAlternatives,oracleGoldRelations:oracle.size,coveredH:hseen.size,coveredF:fseen.size,goldH:hgold.size,goldF:fgold.size};
 }
 return{buildEvidence,propose,score,prepare};
})()
