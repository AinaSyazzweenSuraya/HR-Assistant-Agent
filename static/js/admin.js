const $ = id => document.getElementById(id);
function cell(tr, text) { const td = document.createElement("td"); td.textContent = text; tr.appendChild(td); return td; }
// Same category always gets the same pill colour
const pillClass = s => "pill c" + ([...s].reduce((a, c) => a + c.charCodeAt(0), 0) % 5);

async function loadDocs() {
  const docs = await (await fetch("/api/admin/documents")).json();
  const body = $("docs"); body.replaceChildren();
  if (!docs.length) { const tr = body.insertRow(); const td = cell(tr, "No policies yet. Upload one above."); td.colSpan = 8; }
  docs.forEach(d => {
    const tr = body.insertRow();
    cell(tr, d.name);
    const cat = cell(tr, ""); const pill = document.createElement("span");
    pill.className = pillClass(d.category); pill.textContent = d.category; cat.appendChild(pill);
    cell(tr, "v" + d.version);
    cell(tr, d.access_level);
    cell(tr, d.effective_date);
    const exp = cell(tr, d.expiry_date || "none"); if (!d.expiry_date) exp.className = "muted";
    cell(tr, d.chunk_count);
    const td = cell(tr, ""); const b = document.createElement("button");
    b.className = "link"; b.textContent = "Remove";
    b.onclick = async () => {
      if (!confirm(`Remove ${d.name} v${d.version} from the assistant?`)) return;
      await fetch("/api/admin/documents/" + d.id, { method: "DELETE" }); loadDocs();
    };
    td.appendChild(b);
  });
}

$("upload").addEventListener("submit", async e => {
  e.preventDefault();
  const s = $("status"); s.className = ""; s.textContent = "Uploading…";
  const res = await fetch("/api/admin/documents", { method: "POST", body: new FormData(e.target) });
  const data = await res.json();
  if (res.ok) { s.className = "ok"; s.textContent = `Indexed ${data.name} v${data.version} (${data.chunk_count} chunks).`; e.target.reset(); $("access_level").value = "all"; loadDocs(); }
  else { s.className = "err"; s.textContent = data.error || "Upload failed."; }
});

loadDocs();