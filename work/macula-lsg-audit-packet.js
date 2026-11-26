// In-memory, read-only review packet for source-pinned compact Hebrew alignment maps.
// Outputs contain source text; keep them local/in memory. Flags are diagnostic, not semantic judgments.
// Qualified French ordinals refer to verses within the explicit target chapter.
// A default-verse French gap may be supplied by another native row; reconcile globally before certification.
function auditPacket(hebrew, frenchByScope, nativeVerse, row) {
  const match = /^([^.]+)\.(\d+)\.(\d+)$/.exec(row.french_target);
  if (!match) throw Error("Explicit French target required");
  const scope = `${match[1]}.${match[2]}`, verse = Number(match[3]);
  const projection = frenchByScope[scope];
  if (!projection || projection.verses[String(verse)] === undefined) throw Error("Missing target verse");
  const h = hebrew.words.filter(w => Number(w[1].split("!")[0].split(":").at(-1)) === nativeVerse);
  if (!h.length) throw Error("Missing native verse");
  const tokens = v => {
    const s = projection.verses[String(v)];
    if (typeof s !== "string") throw Error("Missing qualified target verse");
    return s.match(/[\p{L}\p{N}\p{M}]+(?:['’-][\p{L}\p{N}\p{M}]+)*/gu) || [];
  };
  const expand = (expr, max) => {
    if (!/^[1-9]\d*(?:-[1-9]\d*)?$/.test(expr)) throw Error("Invalid ordinal: " + expr);
    const [a,b=a] = expr.split("-").map(Number);
    if (a>b || b>max) throw Error("Out-of-range ordinal: " + expr);
    return Array.from({length:b-a+1},(_,i)=>a+i);
  };
  const usedH = new Set(), usedF = new Set(), lexicalH = new Set(), countsF = new Map(), seen = new Set();
  const relations = row.manual_map.split(";").filter(Boolean).map(map => {
    const m = /^([^:~]+)([:~])([^:~]+)$/.exec(map);
    if (!m) throw Error("Invalid map: " + map);
    const hs = m[1].split(",").flatMap(p=>expand(p,h.length));
    const fs = m[3].split(",").flatMap(p=>{
      let v=verse, range=p;
      if(p.includes(".")) { const a=p.split("."); if(a.length!==2 || !/^[1-9]\d*$/.test(a[0])) throw Error("Unsupported target: "+p);v=Number(a[0]);range=a[1]; }
      const ts=tokens(v);
      return expand(range,ts.length).map(n=>({v,n,t:ts[n-1]}));
    });
    if(new Set(hs).size!==hs.length||new Set(fs.map(x=>`${x.v}.${x.n}`)).size!==fs.length) throw Error("Duplicate ordinal in "+map);
    const key=JSON.stringify([m[2],[...hs].sort((a,b)=>a-b),fs.map(x=>`${x.v}.${x.n}`).sort()]);
    if(seen.has(key))throw Error("Duplicate relation "+map);seen.add(key);
    hs.forEach(n=>{usedH.add(n);if(m[2]===":")lexicalH.add(n)});
    fs.forEach(x=>{const k=`${x.v}.${x.n}`;usedF.add(k);if(m[2]===":")countsF.set(k,(countsF.get(k)||0)+1)});
    return {map,source:hs.map(n=>h[n-1][2]||"∅").join("+"),target:fs.map(x=>x.t).join("+"),kind:m[2]};
  });
  const unlinkedH=h.map((_,i)=>i+1).filter(n=>!usedH.has(n));
  const unlinkedDefaultF=tokens(verse).map((_,i)=>i+1).filter(n=>!usedF.has(`${verse}.${n}`));
  const contextualContentH=h.map((_,i)=>i+1).filter(n=>usedH.has(n)&&!lexicalH.has(n)&&/^(noun|verb|adjective|adverb|proper noun|numeral)$/i.test(h[n-1][4]));
  return {nativeVerse,target:row.french_target,readingText:projection.verses[String(verse)],relations,flags:{unlinkedH,unlinkedDefaultF,contextualContentH,sharedLexicalTargets:[...countsF].filter(([,n])=>n>1).map(([k])=>k)}};
}
if(typeof module!=="undefined")module.exports={auditPacket};
