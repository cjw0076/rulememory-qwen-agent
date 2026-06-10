const $ = (id) => document.getElementById(id);
const api = async (path, body) => {
  const opt = body ? {method:"POST", headers:{"Content-Type":"application/json"}, body:JSON.stringify(body)} : {};
  const r = await fetch(path, opt);
  return r.json();
};
const esc = (s)=> (s??"").replace(/[&<>]/g, c=>({"&":"&amp;","<":"&lt;",">":"&gt;"}[c]));

const SAMPLE1 = "Global AI Hackathon Series with Qwen Cloud — MemoryAgent track. " +
  "The final submission deadline is 2026-07-10T23:59:00+00:00 on Devpost. " +
  "Teams may have at most 4 members and must register before kickoff. " +
  "Submissions must use a Qwen model via Qwen Cloud MaaS. " +
  "We should still use Python 2 for the build scripts since that is what the old runner expected. " +
  "The grand prize is 10000 USD.";
const SAMPLE2 = "Update from the organizers: the runner was upgraded, so the toolchain now requires Python 3.11. " +
  "Also confirmed: judging is done by Qwen and Alibaba Cloud engineers.";

function factCard(f){
  const badges = `<span class="badge b-${f.type}">${f.type}</span>` +
    (f.stale?'<span class="badge b-stale">stale</span>':'');
  const due = f.due_at?`<div class="prov">due: ${esc(f.due_at)}</div>`:'';
  return `<div class="fact">${badges}<span class="stmt">${esc(f.statement)}</span>${due}</div>`;
}

async function refreshStatus(){
  const s = await api("/api/status");
  $("status").textContent = `backend: ${s.backend} · embedder: ${s.embedder} · ${s.entries} entries`;
}

async function doIngest(){
  const text = $("ingestText").value.trim();
  if(!text) return;
  $("ingestOut").innerHTML = '<div class="empty">Qwen is extracting facts…</div>';
  const res = await api("/api/ingest", {text, source_id:$("sourceId").value||"ui-input"});
  let html = `<div class="hint">${res.added_count} facts extracted &amp; stored.</div>`;
  html += (res.facts||[]).map(factCard).join("");
  if(res.conflicts && res.conflicts.length){
    html += '<div class="hint" style="margin-top:10px">Conflicts resolved (older superseded):</div>';
    res.conflicts.forEach(c=>{
      html += `<div class="warn">⊘ "${esc(c.superseded_statement)}" → superseded by "${esc(c.by_statement)}" (${esc(c.reason)})</div>`;
    });
  }
  $("ingestOut").innerHTML = html;
  await refreshStatus(); await refreshMemory(); await refreshTranscript();
}

async function doAsk(){
  const q = $("question").value.trim();
  if(!q) return;
  $("askOut").innerHTML = '<div class="empty">Recalling memory &amp; asking Qwen…</div>';
  const res = await api("/api/ask", {question:q, k:5});
  let html = `<div class="answer">${esc(res.answer)}</div>`;
  (res.warnings||[]).forEach(w=> html += `<div class="warn">⚠ ${esc(w)}</div>`);
  if(res.recalled && res.recalled.length){
    html += '<div class="hint" style="margin-top:8px">Semantic recall hits:</div>';
    res.recalled.forEach(h=>{
      html += `<div class="fact"><span class="score">${h.score.toFixed(3)}</span>`+
        `<span class="badge b-${h.type}">${h.type}</span>`+
        (h.stale?'<span class="badge b-stale">stale</span>':'')+
        `<span class="stmt">${esc(h.statement)}</span></div>`;
    });
  }
  if(res.citations && res.citations.length){
    html += '<div class="prov" style="margin-top:6px">provenance: '+
      res.citations.map(c=>`#${c.n}→${esc(c.source_id)}[${c.char_span[0]}:${c.char_span[1]}]`).join(", ")+'</div>';
  }
  $("askOut").innerHTML = html;
  await refreshTranscript();
}

async function doRecall(){
  const q = $("question").value.trim(); if(!q) return;
  const res = await api("/api/recall", {question:q, k:6});
  let html = '<div class="hint">Pure semantic recall (no LLM):</div>';
  res.hits.forEach(h=>{
    html += `<div class="fact"><span class="score">${h.score.toFixed(3)}</span>`+
      `<span class="badge b-${h.type}">${h.type}</span>`+
      `<span class="stmt">${esc(h.statement)}</span></div>`;
  });
  $("askOut").innerHTML = html;
}

async function refreshMemory(){
  const m = await api("/api/memory");
  $("summary").textContent = m.summary || "";
  if(!m.table.length){ $("memTable").innerHTML='<div class="empty">Memory is empty. Ingest something.</div>'; return; }
  let rows = m.table.map(r=>{
    const cls = r.status==="superseded"?"superseded":(r.stale?"stale":"");
    const tags = `<span class="badge b-${r.type}">${r.type}</span>`+
      (r.status==="superseded"?'<span class="badge b-superseded">superseded</span>':'')+
      (r.stale && r.status!=="superseded"?'<span class="badge b-stale">stale</span>':'');
    return `<tr class="${cls}"><td>${tags}</td><td>${esc(r.statement)}</td>`+
      `<td class="prov">${esc(r.source.source_id)}[${r.source.char_start}:${r.source.char_end}]<br>${esc(r.session_id)}</td></tr>`;
  }).join("");
  $("memTable").innerHTML = `<table><thead><tr><th>type</th><th>statement</th><th>provenance</th></tr></thead><tbody>${rows}</tbody></table>`;
}

async function refreshTranscript(){
  const t = await api("/api/transcript");
  if(!t.transcript.length){ $("transcript").innerHTML='<div class="empty">No steps yet.</div>'; return; }
  $("transcript").innerHTML = t.transcript.map(e=>{
    const extra = e.step==="facts_extracted"?` (${e.count} facts)` :
                  e.step==="recall"?` (${(e.hits||[]).length} hits)` : "";
    return `<div class="tev">${e.ts.split("T")[1]?.replace("+00:00","")||""} · <b>${e.step}</b>${extra} · ${e.reasoner}</div>`;
  }).join("");
}

$("ingestBtn").onclick = doIngest;
$("askBtn").onclick = doAsk;
$("recallBtn").onclick = doRecall;
$("refreshMem").onclick = refreshMemory;
$("seed1").onclick = ()=>{$("ingestText").value=SAMPLE1; $("sourceId").value="contest-rules-v1";};
$("seed2").onclick = ()=>{$("ingestText").value=SAMPLE2; $("sourceId").value="organizer-update-v2";};
$("resetBtn").onclick = async()=>{ await api("/api/reset",{}); await refreshStatus(); await refreshMemory(); await refreshTranscript(); $("ingestOut").innerHTML=""; $("askOut").innerHTML=""; };
$("question").addEventListener("keydown",e=>{if(e.key==="Enter")doAsk();});

refreshStatus(); refreshMemory(); refreshTranscript();
