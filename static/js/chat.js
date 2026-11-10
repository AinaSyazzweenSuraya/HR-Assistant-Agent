const log = document.getElementById("log");
const input = document.getElementById("input");
const sendBtn = document.getElementById("send");
let history = [];
let busy = false;

function el(tag, cls, text) {
  const e = document.createElement(tag);
  if (cls) e.className = cls;
  if (text !== undefined) e.textContent = text;
  return e;
}

// Escape first, then allow **bold**, "- " bullets and line breaks.
function format(text) {
  const d = document.createElement("div");
  d.textContent = text;
  return d.innerHTML
    .replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>")
    .replace(/^\s*[-*]\s+/gm, "• ")
    .replace(/\n/g, "<br>");
}

function scroll() { log.scrollTop = log.scrollHeight; }

function addUser(text) {
  document.getElementById("empty")?.remove();
  log.appendChild(el("div", "msg user", text));
  scroll();
}

function addBot(data, cls) {
  const box = el("div", "msg bot " + (cls || ""));
  const body = el("div", "text");
  body.innerHTML = format(data.answer || data.error);
  box.appendChild(body);

  if (data.sources && data.sources.length) {
    const det = el("details", "sources");
    det.open = true;
    det.appendChild(el("summary", "", `Policy references (${data.sources.length})`));
    data.sources.forEach(s => {
      const row = el("div", "source");
      row.appendChild(el("span", "tag", `[${s.id}]`));
      const info = el("div");
      info.appendChild(el("span", "meta", `${s.document} v${s.version}`));
      const where = [s.section, s.page ? `page ${s.page}` : ""].filter(Boolean).join(", ");
      if (where) info.appendChild(el("span", "where", ` — ${where}`));
      row.appendChild(info);
      row.appendChild(el("div", "snip", s.snippet));
      det.appendChild(row);
    });
    box.appendChild(det);
  }
  log.appendChild(box);
  scroll();
}

function addTyping() {
  const box = el("div", "msg bot");
  const t = el("div", "typing");
  t.setAttribute("aria-label", "Looking up policies");
  t.append(el("i"), el("i"), el("i"));
  box.appendChild(t);
  log.appendChild(box);
  scroll();
  return box;
}

async function ask(question) {
  question = question.trim();
  if (!question || busy) return;
  busy = true; sendBtn.disabled = true;
  addUser(question);
  input.value = ""; input.style.height = "auto";
  const typing = addTyping();
  try {
    const res = await fetch("/api/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ message: question, history: history.slice(-6) }),
    });
    if (res.status === 401) { window.location = "/login"; return; }
    const data = await res.json();
    typing.remove();
    if (!res.ok) {
      addBot({ error: data.error || "Something went wrong. Try again." }, "error");
    } else {
      addBot(data, data.answered ? "" : "unanswered");
      history.push({ role: "user", content: question }, { role: "assistant", content: data.answer });
    }
  } catch (e) {
    typing.remove();
    addBot({ error: "Could not reach the server. Check your connection and try again." }, "error");
  } finally {
    busy = false; sendBtn.disabled = false; input.focus();
  }
}

sendBtn.addEventListener("click", () => ask(input.value));
input.addEventListener("keydown", e => {
  if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); ask(input.value); }
});
input.addEventListener("input", () => {
  input.style.height = "auto";
  input.style.height = Math.min(input.scrollHeight, 140) + "px";
});
document.querySelectorAll(".chip").forEach(c => c.addEventListener("click", () => ask(c.textContent)));
