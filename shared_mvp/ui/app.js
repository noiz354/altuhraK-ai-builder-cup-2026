let project, current;
const byId = id => document.getElementById(id);
const stringify = value => JSON.stringify(value, null, 2);
async function api(path, method='GET', body) {
  const options = {method, headers: {'Content-Type':'application/json'}};
  if (body !== undefined) options.body = stringify(body);
  const res = await fetch(path, options);
  const value = await res.json();
  if (!res.ok) throw new Error(typeof value.detail === 'string' ? value.detail : stringify(value.detail));
  return value;
}
function notify(text) { byId('notice').textContent = text; }
function printable(value) { return typeof value === 'object' ? JSON.stringify(value) : String(value ?? '—'); }
function renderResult(target, value) {
  const node = byId(target); node.replaceChildren(); node.classList.remove('empty');
  if (!value) { node.textContent = 'Tidak tersedia.'; return; }
  if(value.nodes && value.edges)drawGraph(node,value);
  if(value.forecast && value.forecast.length)drawForecast(node,value.forecast);
  for (const [name, content] of Object.entries(value)) {
    const label = document.createElement('div'); label.className='result-label'; label.textContent=name.replaceAll('_',' '); node.append(label);
    if (Array.isArray(content) && content.length && typeof content[0] === 'object') {
      const wrap = document.createElement('div'); wrap.className='table-wrap';
      const table = document.createElement('table'); const header = document.createElement('tr');
      const keys = Object.keys(content[0]);
      for (const key of keys) { const th=document.createElement('th'); th.textContent=key.replaceAll('_',' '); header.append(th); }
      const thead=document.createElement('thead'); thead.append(header); table.append(thead);
      const tbody=document.createElement('tbody');
      for (const row of content) { const tr=document.createElement('tr'); for(const key of keys) {const td=document.createElement('td');td.textContent=printable(row[key]);tr.append(td);}tbody.append(tr); }
      table.append(tbody); wrap.append(table); node.append(wrap);
    } else {
      const pre=document.createElement('pre');pre.textContent=printable(content);node.append(pre);
    }
  }
}
function canvasFor(node){const canvas=document.createElement('canvas');canvas.width=640;canvas.height=260;canvas.style.width='100%';canvas.style.height='auto';canvas.setAttribute('role','img');node.append(canvas);return canvas;}
function drawGraph(node,value){
  const canvas=canvasFor(node);canvas.setAttribute('aria-label','Grafik jaringan transaksi dari evidence');const ctx=canvas.getContext('2d');const nodes=value.nodes.slice(0,40),positions={};
  nodes.forEach((id,i)=>{const angle=i*Math.PI*2/nodes.length;positions[id]=[320+230*Math.cos(angle),130+90*Math.sin(angle)];});
  ctx.strokeStyle='#b6c9bc';ctx.fillStyle='#718e7e';
  for(const edge of value.edges){const a=positions[edge.from_account_id],b=positions[edge.to_account_id];if(!a||!b)continue;ctx.beginPath();ctx.moveTo(...a);ctx.lineTo(...b);ctx.stroke();const angle=Math.atan2(b[1]-a[1],b[0]-a[0]);const x=b[0]-12*Math.cos(angle),y=b[1]-12*Math.sin(angle);ctx.beginPath();ctx.moveTo(x,y);ctx.lineTo(x-8*Math.cos(angle-.4),y-8*Math.sin(angle-.4));ctx.lineTo(x-8*Math.cos(angle+.4),y-8*Math.sin(angle+.4));ctx.fill();}
  for(const [id,p] of Object.entries(positions)){ctx.fillStyle='#1e6253';ctx.beginPath();ctx.arc(...p,8,0,2*Math.PI);ctx.fill();ctx.fillStyle='#173032';ctx.font='11px system-ui';ctx.textAlign='center';ctx.fillText(id,p[0],p[1]+22);}
}
function drawForecast(node,forecast){
  const canvas=canvasFor(node);canvas.setAttribute('aria-label','Grafik forecast baseline');const ctx=canvas.getContext('2d');const max=Math.max(1,...forecast.map(p=>p.units));ctx.strokeStyle='#1e6253';ctx.lineWidth=2;ctx.beginPath();forecast.forEach((p,i)=>{const x=40+i*560/Math.max(1,forecast.length-1),y=210-p.units/max*160;i?ctx.lineTo(x,y):ctx.moveTo(x,y);});ctx.stroke();ctx.fillStyle='#173032';ctx.font='11px system-ui';forecast.forEach((p,i)=>{const x=40+i*560/Math.max(1,forecast.length-1),y=210-p.units/max*160;ctx.beginPath();ctx.arc(x,y,4,0,2*Math.PI);ctx.fill();ctx.fillText(`${p.units.toFixed(1)} units`,x,y-10);ctx.fillText(p.date,x,235);});
}
async function display(run) {
  current=run; byId('status').textContent=`${run.state} / ${run.status} / rev ${run.revision}`;
  renderResult('baseline',run.baseline_result);renderResult('ai',run.ai_result);
  byId('draft').value=stringify(run.draft);
  byId('warnings').textContent=run.errors.map(e=>`${e.code}: ${e.message}`).join('\n');
  byId('usage').textContent=stringify(run.usage);
  const holder=byId('evidence');holder.replaceChildren();
  for(const item of run.evidence) {const detail=document.createElement('details');const summary=document.createElement('summary');summary.textContent=item.evidence_id;const pre=document.createElement('pre');pre.textContent=stringify(item.source_excerpt);detail.append(summary,pre);holder.append(detail);}
  const ready=['completed','partial'].includes(run.state);
  for(const id of ['save','approve','reject']) byId(id).disabled=!ready;
  byId('export').disabled=!run.review || run.review.decision!=='approve' || run.review.revision!==run.revision;
  byId('review-status').textContent=run.review ? `${run.review.decision} · revision ${run.review.revision} · ${run.review.actor}` : 'Belum ada review untuk revisi ini.';
  byId('audit').textContent=stringify(await api(`/api/runs/${run.run_id}/audit`));
}
const labels={currency:'Mata uang',reference:'Referensi transaksi',item:'Barang',question:'Pertanyaan',query:'Kebutuhan atau pencarian',budget_minor:'Anggaran (unit minor)',threshold:'Ambang review',forecast_date:'Tanggal forecast',horizon_days:'Jumlah hari forecast',as_of:'Waktu analisis',output_language:'Bahasa hasil',image_id:'Gambar',doc_id:'Dokumen',hint_level:'Tingkat petunjuk',student_answer:'Jawaban pelajar',machine_id:'Mesin',machine_type:'Jenis mesin',symptom_id:'Gejala',seed_account_id:'Akun awal',period:'Periode',area_id:'Wilayah',meeting_id:'Rapat',batch_id:'Batch',buyer_id:'Pembeli',access_group:'Grup akses'};
function parameterForm(params){
  const holder=byId('parameter-form');holder.replaceChildren();
  for(const [key,value] of Object.entries(params)){
    if(typeof value==='object')continue;
    const label=document.createElement('label');label.textContent=labels[key]||key.replaceAll('_',' ');
    const input=document.createElement('input');input.id=`param-${key}`;label.htmlFor=input.id;input.type=typeof value==='number'?'number':'text';if(typeof value==='number')input.step='any';input.value=value;
    input.addEventListener('input',()=>{try{const currentParams=JSON.parse(byId('params').value);currentParams[key]=typeof value==='number'?Number(input.value):input.value;byId('params').value=stringify(currentParams);}catch(e){notify('Parameter JSON perlu diperbaiki sebelum mengubah form.');}});
    holder.append(label,input);
  }
}
async function loadFixture() {const fixture=await api('/api/fixture');byId('data').value=stringify(fixture.data);byId('params').value=stringify(fixture.params);const counts=Object.entries(fixture.data).filter(([,v])=>Array.isArray(v)).map(([k,v])=>`${k.replaceAll('_',' ')}: ${v.length}`).join(' · ');byId('data-preview').textContent=counts;parameterForm(fixture.params);notify('Contoh sintetis dimuat. Anda dapat mengubah skenario sebelum menjalankan.');}
function handle(id, operation) {byId(id).addEventListener('click',async()=>{try{await operation();}catch(error){notify(error.message);}});}
handle('fixture',loadFixture);
handle('run',async()=>{
  byId('run').disabled=true;notify('Memproses…');
  try {
    const imported=await api('/api/datasets','POST',{project_id:project.id,data:JSON.parse(byId('data').value)});
    const started=await api('/api/runs','POST',{dataset_id:imported.dataset_id,mode:byId('mode').value,params:JSON.parse(byId('params').value)});
    let run;
    for(let i=0;i<180;i++){run=await api(`/api/runs/${started.run_id}`);if(!['queued','running'].includes(run.state))break;await new Promise(r=>setTimeout(r,500));}
    await display(run);notify(['queued','running'].includes(run.state)?'Run masih berjalan; jangan mulai run baru.':'Analisis selesai. Periksa hasil dan evidence sebelum review.');
  } finally {byId('run').disabled=false;}
});
handle('save',async()=>{await display(await api(`/api/runs/${current.run_id}/draft`,'PATCH',{expected_revision:current.revision,draft:JSON.parse(byId('draft').value)}));notify('Revisi tersimpan. Persetujuan sebelumnya dibatalkan.');});
for(const decision of ['approve','reject']) handle(decision,async()=>{await api(`/api/runs/${current.run_id}/reviews`,'POST',{expected_revision:current.revision,decision,comment:byId('comment').value});await display(await api(`/api/runs/${current.run_id}`));notify(`Review ${decision} tersimpan.`);});
handle('export',async()=>{const output=await api(`/api/runs/${current.run_id}/export`);const url=URL.createObjectURL(new Blob([stringify(output)],{type:'application/json'}));const a=document.createElement('a');a.href=url;a.download=`${project.id}-${current.run_id}.json`;a.click();URL.revokeObjectURL(url);});
(async()=>{try{project=await api('/api/project');document.title=project.name;byId('title').textContent=project.name;byId('track').textContent=`${project.id} · ${project.track}`;byId('goal').textContent=project.goal;byId('limits').textContent=project.limitations;byId('schema').textContent=stringify({input:project.inputs,params:project.params,output:project.output});await loadFixture();}catch(e){notify(e.message);}})();


function setTab(name){document.querySelectorAll('.view').forEach(v=>v.classList.toggle('active',v.id===`view-${name}`));document.querySelectorAll('.tab').forEach(b=>b.classList.toggle('active',b.dataset.tab===name));}
document.addEventListener('DOMContentLoaded',()=>{let fallback=false;document.querySelectorAll('.tab').forEach(b=>b.addEventListener('click',()=>setTab(b.dataset.tab)));const target=new URLSearchParams(location.hash.slice(1)).get('tab');setTab(target||'crew');});
const oldDisplay=display;
display=async function(run){const result=await oldDisplay(run);const analytics=byId('analytics-summary');if(analytics)analytics.textContent=stringify({state:run.state,status:run.status,respon_waktu:run.usage?.latency_ms||run.usage?.latency_ms,provider:run.usage?.model_id||null});const pipeline=byId('pipeline-status');if(pipeline)pipeline.textContent=`${run.state}/${run.status} · revisi ${run.revision} · evidence ${run.evidence?.length||0}`;return result;};
