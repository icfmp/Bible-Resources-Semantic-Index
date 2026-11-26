#!/usr/bin/env node
"use strict";
// Research-only local runner. No network, external packages, or automatic acceptance.
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");
const root = path.resolve(__dirname, "../links/alignments/macula-lsg");
const read = p => JSON.parse(fs.readFileSync(p, "utf8"));
const engine = vm.runInNewContext(fs.readFileSync(path.join(__dirname, "macula-lsg-assist-prototype.js"), "utf8"));
const receipt = read(path.join(__dirname, "macula-lsg-assist-pilot.json"));
const options = receipt.selected;
const n3 = n => String(n).padStart(3, "0");
const output = x => process.stdout.write(JSON.stringify(x, null, 2) + "\n");
function source(book, native, chapter, g = undefined) {
    if (!/^[A-Za-z0-9]+$/.test(book) || !/^[A-Za-z0-9]+$/.test(native) ||
        !Number.isInteger(chapter) || chapter < 1) throw Error("Invalid source locator");
    const filename = n3(chapter) + ".json";
    return {scope: book + "." + chapter, book, native, chapter, g,
        h: read(path.join(root, "sources/macula-hebrew", native, filename)),
        f: read(path.join(root, "sources/lsg", book, filename))};
}
function auditedChapters() {
    const found = [];
    for (const dir of fs.readdirSync(root, {withFileTypes: true})) {
        if (!dir.isDirectory() || dir.name === "sources") continue;
        for (const file of fs.readdirSync(path.join(root, dir.name))) {
            if (!/^\d{3}\.json$/.test(file)) continue;
            const g = read(path.join(root, dir.name, file));
            if (g.editorial_review?.passes !== 2) continue;
            if (!g.sources?.macula?.path?.startsWith("WLC/")) continue;
            const m = /^(\w+)\.(\d+)\./.exec(g.scope);
            const native = /\/\d+-([A-Za-z0-9]+)-\d+-lowfat\.xml$/.exec(g.sources.macula.path);
            if (!m || !native || Number(m[2]) !== Number(file.slice(0, 3))) throw Error("Invalid audited ledger " + file);
            found.push(source(m[1], native[1], Number(m[2]), g));
        }
    }
    const seen = new Set();
    for (const c of found) {
        if (seen.has(c.scope)) throw Error("Duplicate audited chapter " + c.scope);
        seen.add(c.scope);
        engine.prepare(c);
    }
    return found.sort((a,b) => a.scope.localeCompare(b.scope));
}
function aggregate(rows) {
    if (!rows.length) throw Error("No benchmark rows");
    return Object.fromEntries(Object.keys(rows[0]).filter(k=>k !== "scope")
        .map(k=>[k,rows.reduce((s,x)=>s+x[k],0)]));
}
function benchmark(pilot) {
    const all = auditedChapters();
    const dev = receipt.development[0].rows.map(x=>x.scope);
    const holdout = receipt.held_out.map(x=>x.scope);
    const held = new Set([...dev, ...holdout]);
    const training = pilot ? all.filter(x=>receipt.additional_training.includes(x.scope)) : all.filter(x=>!held.has(x.scope));
    const seed = pilot ? read(path.join(__dirname, "macula-lsg-numbers-021-deuteronomy-004-candidate-bank.json")) : null;
    const bank = engine.buildEvidence(training, seed);
    if ([...held].some(s=>bank.scopes.has(s))) throw Error("Held-out chapter leaked");
    const select = scopes => scopes.map(s=>{
        const c = all.find(x=>x.scope===s);
        if (!c) throw Error("Missing benchmark chapter " + s);
        return engine.score(c, engine.propose(c,bank,options));
    });
    const devRows = select(dev), holdRows = select(holdout);
    output({status:"benchmark_not_editorial_audit",mode:pilot?"pilot":"full_corpus",
        auditedInventory:all.length, trainingScopes:[...bank.scopes].sort(), exactKeys:bank.exact.size,lemmaKeys:bank.lemma.size,
        options,skipped:bank.skipped,development:devRows,developmentTotal:aggregate(devRows),holdout:holdRows,holdoutTotal:aggregate(holdRows)});
}
function streamingBenchmark() {
    const all = auditedChapters();
    const dev = receipt.development[0].rows.map(x=>x.scope);
    const holdout = receipt.held_out.map(x=>x.scope);
    const excluded = new Set([...dev, ...holdout]);
    const training = all.filter(x=>!excluded.has(x.scope));
    const held = holdout.map(s=>{
        const c = all.find(x=>x.scope===s);
        if(!c) throw Error("Missing holdout chapter " + s);
        return c;
    });
    const stream = vm.runInNewContext(fs.readFileSync(path.join(__dirname, "macula-lsg-assist-streaming.js"), "utf8"));
    const q = stream.queries(held), a = {denom:{}, candidates:{}};
    const skipped = {nonContiguous:0,otherVerse:0,unknownOriginal:0};
    for(const c of training) {
        const scan=stream.scan(c,q);
        stream.merge(a,scan);
        for(const k of Object.keys(skipped)) skipped[k]+=scan.skipped[k];
    }
    const predictions=stream.predictions(q,a,options);
    const rows=held.map((c,i)=>engine.score(c,predictions[i]));
    output({status:"benchmark_not_editorial_audit",mode:"streamed_full_corpus",
        auditedInventory:all.length,trainingScopes:training.map(x=>x.scope).sort(),
        excludedDevelopment:dev,holdout:rows,holdoutTotal:aggregate(rows),options,skipped,
        queryCount:q.byId.length,candidateTierCount:Object.keys(a.candidates).length});
}

function verseMapping(c, declaration) {
    const p = engine.prepare(c,false);
    if (declaration === "identity") {
        if (p.groups.size !== p.french.size || [...p.groups.keys()].some(v=>!p.french.has(v)))
            throw Error("Identity verse inventory differs " + c.scope);
        return {};
    }
    if (!declaration || typeof declaration !== "object" || Array.isArray(declaration))
        throw Error("Explicit verse mapping or reviewed identity declaration required " + c.scope);
    for (const v of p.groups.keys()) if (!Number.isInteger(declaration[v]) || !p.french.has(declaration[v]))
        throw Error("Missing or unsupported same-chapter target " + c.scope + "." + v);
    return declaration;
}
function packet(plan) {
    const all = auditedChapters(), bank = engine.buildEvidence(all);
    if (!Array.isArray(plan.chapters) || !plan.chapters.length) throw Error("Missing cohort plan");
    const chapters = plan.chapters.map(spec=>{
        const c = source(spec.book,spec.native,spec.chapter), p = engine.prepare(c,false);
        const prediction = engine.propose(c,bank,options,verseMapping(c,spec.versification));
        const rows = prediction.rows.map(row=>{
            const h = p.groups.get(row.nativeVerse), text = Array.from(c.f.verses[row.frenchVerse]);
            return {nativeVerse:row.nativeVerse,frenchVerse:row.frenchVerse,
                h:h.map((w,i)=>[i+1,w[2],w[3],w[4],w[5]]),
                f:p.french.get(row.frenchVerse).map((w,i)=>[i+1,text.slice(w.start,w.end).join("")]),
                prefill:row.prefill.map(a=>a.h.join(",")+":"+a.f.join(",")),
                prefillEvidence:row.prefill,
                unfilledH:row.unfilledH,unfilledF:row.unfilledF,alternativeCount:row.review.length,
                ...(plan.includeAlternatives?{alternatives:row.review}:{})};
        });
        return {scope:c.scope,book:c.book,native:c.native,chapter:c.chapter,
            sourceLsgSha256:c.f.reading_text_sha256,sourceMaculaBlob:c.h.git_blob,rows};
    });
    output({status:"unreviewed_private_editorial_packet",trainingScopes:[...bank.scopes].sort(),skipped:bank.skipped,options,chapters});
}
function ordinals(s, max) {
    const values = [];
    for (const part of s.split(",")) {
        const m = /^(\d+)(?:-(\d+))?$/.exec(part);
        if (!m) throw Error("Invalid ordinal " + part);
        const a = +m[1], b = +(m[2]??m[1]);
        if (a<1 || b<a || b>max) throw Error("Ordinal outside source inventory " + part);
        for(let i=a;i<=b;i++) values.push(i);
    }
    if (new Set(values).size!==values.length) throw Error("Duplicate ordinal");
    return values;
}
function apply(p, edits) {
    if (p.status !== "unreviewed_private_editorial_packet") throw Error("Unexpected packet");
    const chapters = p.chapters.map(ch=>{
        const c = source(ch.book,ch.native,ch.chapter), src = engine.prepare(c,false);
        if (c.h.git_blob!==ch.sourceMaculaBlob || c.f.reading_text_sha256!==ch.sourceLsgSha256) throw Error("Source locks changed "+ch.scope);
        if (ch.rows.length!==src.groups.size || new Set(ch.rows.map(r=>r.nativeVerse)).size!==src.groups.size)
            throw Error("Incomplete chapter packet "+ch.scope);
        const draft = {};
        for(const row of ch.rows) {
            const edit = edits[ch.scope]?.[row.nativeVerse];
            if (edit?.confirmed!==true) throw Error("Every verse requires explicit editorial confirmation "+ch.scope+"."+row.nativeVerse);
            const hmax=src.groups.get(row.nativeVerse)?.length, fmax=src.french.get(row.frenchVerse)?.length;
            if (!hmax || !fmax) throw Error("Unknown source/target verse");
            const drop=edit.drop??[], add=(edit.add??"").split(";").map(s=>s.trim()).filter(Boolean);
            if(!Array.isArray(drop)||drop.some(s=>!row.prefill.includes(s))) throw Error("Drop must identify exact proposal");
            const relations=[...row.prefill.filter(s=>!drop.includes(s)),...add];
            const sigs=new Set();
            for(const rel of relations) {
                const m=/^([\d,-]+)([:~])([\d,-]+)$/.exec(rel);
                if(!m) throw Error("Only same-verse ordinal relations supported by this prototype; use existing compact rebuild for cross-verse links");
                const sig=JSON.stringify([ordinals(m[1],hmax).sort((a,b)=>a-b),m[2],ordinals(m[3],fmax).sort((a,b)=>a-b)]);
                if(sigs.has(sig)) throw Error("Duplicate relation");
                sigs.add(sig);
            }
            draft[row.nativeVerse]={french_verse:row.frenchVerse,map:relations.join(";"),...(edit.note?{note:edit.note}:{})};
        }
        return {scope:ch.scope,sourceLsgSha256:ch.sourceLsgSha256,sourceMaculaBlob:ch.sourceMaculaBlob,draft};
    });
    output({status:"explicitly_confirmed_first_pass_pending_second_pass_audit",chapters});
}
const [command,arg1,arg2]=process.argv.slice(2);
if(command==="benchmark") benchmark(arg1==="--pilot");
else if(command==="benchmark-stream") streamingBenchmark();
else if(command==="packet"&&arg1) packet(read(arg1));
else if(command==="apply"&&arg1&&arg2) apply(read(arg1),read(arg2));
else throw Error("Usage: node work/macula-lsg-assist-runner.cjs benchmark [--pilot] | benchmark-stream | packet PLAN.json | apply PACKET.json EDITS.json");
