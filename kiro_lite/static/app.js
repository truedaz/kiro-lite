// Simple front-end glue for Kiro-Lite
const $ = (q)=>document.querySelector(q);
const ol = $("#tasks");
const promptEl = $("#prompt");
const specEl = $("#spec");
const fileList = $("#file-list");
const newFile = $("#new-file");
const currentFile = $("#current-file");
const btnSave = $("#save-file");
const btnOpen = $("#open-file");
const preview = $("#preview");

require.config({ paths: { 'vs': 'https://cdnjs.cloudflare.com/ajax/libs/monaco-editor/0.52.0/min/vs' } });
let editor;
require(['vs/editor/editor.main'], function() {
  editor = monaco.editor.create(document.getElementById('monaco'), {
    value: "<!-- Select a file from the list to edit -->",
    language: "html",
    automaticLayout: true,
    fontSize: 14
  });
});

async function refreshFiles(){
  const res = await fetch('/api/files');
  const data = await res.json();
  fileList.innerHTML='';
  (data.files || []).forEach(f=>{
    const li = document.createElement('li');
    li.innerHTML = `<span>${f}</span><button data-open="${f}">Open</button>`;
    fileList.appendChild(li);
  });
}

async function openFile(path){
  const res = await fetch('/api/files?path='+encodeURIComponent(path));
  const data = await res.json();
  currentFile.textContent = data.path;
  editor.setValue(data.content || '');
  const ext = (path.split('.').pop() || '').toLowerCase();
  const lang = ext==='js'?'javascript':ext==='css'?'css':ext==='json'?'json':'html';
  monaco.editor.setModelLanguage(editor.getModel(), lang);
  updatePreview();
}

function updatePreview(){
  fetch('/api/files?path=index.html').then(async r=>{
    if(!r.ok) return;
    const d = await r.json();
    const blob = new Blob([d.content], {type:'text/html'});
    const url = URL.createObjectURL(blob);
    preview.src = url;
  });
}

fileList.addEventListener('click', (e)=>{
  const btn = e.target.closest('button[data-open]');
  if(btn){
    openFile(btn.getAttribute('data-open'));
  }
});

$("#create-file").addEventListener('click', async ()=>{
  const p = newFile.value.trim();
  if(!p) return;
  await fetch('/api/files',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({path:p,content:''})});
  newFile.value='';
  refreshFiles();
});

$("#refresh-files").addEventListener('click', refreshFiles);

btnSave.addEventListener('click', async ()=>{
  const path = currentFile.textContent;
  if(!path || path==='No file') return;
  await fetch('/api/files',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({path, content: editor.getValue()})});
  updatePreview();
});

btnOpen.addEventListener('click', ()=>{
  const p = prompt("Path to open:");
  if(p) openFile(p);
});

$("#btn-generate").addEventListener('click', async ()=>{
  const res = await fetch('/api/spec',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({prompt: promptEl.value})});
  const data = await res.json();
  specEl.value = data.raw || '';
});

$("#btn-derive").addEventListener('click', async ()=>{
  const res = await fetch('/api/tasks',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({raw: specEl.value})});
  const data = await res.json();
  ol.innerHTML='';
  (data.tasks||[]).forEach(t=>{
    const li = document.createElement('li');
    li.textContent = t;
    ol.appendChild(li);
  });
});

$("#btn-apply").addEventListener('click', async ()=>{
  const next = ol.querySelector('li');
  const task = next ? next.textContent : 'Scaffold minimal app';
  const res = await fetch('/api/apply',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({task})});
  const data = await res.json();
  await refreshFiles();
  updatePreview();
  if(next) next.remove();
});

// initial
refreshFiles();
updatePreview();
