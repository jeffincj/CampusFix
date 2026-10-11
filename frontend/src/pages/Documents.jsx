// Admins upload college rule PDFs; the assistant answers rule questions from them (RAG).
import { useEffect, useState } from "react";
import { api } from "../api.js";
import { formatDate } from "../constants.js";

export default function Documents() {
  const [documents, setDocuments] = useState([]);
  const [file, setFile] = useState(null);
  const [title, setTitle] = useState("");
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState({ type: "", text: "" });

  const load = () => api("/documents/").then(setDocuments).catch((err) => setMessage({ type: "error", text: err.message }));
  useEffect(() => { load(); }, []);

  async function upload(event) {
    event.preventDefault();
    if (!file) return setMessage({ type: "error", text: "Choose a PDF file first." });
    if (!file.name.toLowerCase().endsWith(".pdf")) return setMessage({ type: "error", text: "Only PDF files are accepted." });
    if (file.size > 10 * 1024 * 1024) return setMessage({ type: "error", text: "The PDF must be 10 MB or smaller." });

    const form = new FormData();
    form.append("file", file);
    if (title.trim()) form.append("title", title.trim());
    setBusy(true);
    try {
      const doc = await api("/documents/", { method: "POST", form });
      setMessage({ type: "success", text: `Uploaded “${doc.title}”: ${doc.pages} pages, ${doc.chunks} chunks indexed.` });
      setFile(null);
      setTitle("");
      event.target.reset();
      load();
    } catch (err) {
      setMessage({ type: "error", text: err.message });
    } finally {
      setBusy(false);
    }
  }

  async function remove(doc) {
    if (!window.confirm(`Delete “${doc.title}”? The assistant will stop using it.`)) return;
    try {
      await api(`/documents/${doc.id}/`, { method: "DELETE" });
      load();
    } catch (err) {
      setMessage({ type: "error", text: err.message });
    }
  }

  return (
    <div>
      <div className="page-head"><h1>Rule documents</h1></div>
      <p className="muted">The assistant answers rule questions only from these PDFs and cites file and page.</p>
      {message.text && <div className={`alert ${message.type}`}>{message.text}</div>}

      <form className="card filters" onSubmit={upload}>
        <input type="file" accept="application/pdf,.pdf" onChange={(e) => setFile(e.target.files[0] || null)} aria-label="PDF file" />
        <input placeholder="Title (optional)" value={title} onChange={(e) => setTitle(e.target.value)} maxLength={200} />
        <button className="button" disabled={busy}>{busy ? "Uploading…" : "Upload PDF"}</button>
      </form>

      <div className="card table-card">
        <table className="table">
          <thead><tr><th>Title</th><th>File</th><th className="num">Pages</th><th className="num">Chunks</th><th>Uploaded</th><th /></tr></thead>
          <tbody>
            {documents.map((d) => (
              <tr key={d.id}>
                <td>{d.title}</td><td>{d.file_name}</td><td className="num">{d.pages}</td><td className="num">{d.chunks}</td>
                <td className="small">{formatDate(d.created_at)}</td>
                <td><button className="link danger" onClick={() => remove(d)}>Delete</button></td>
              </tr>
            ))}
            {documents.length === 0 && <tr><td colSpan={6} className="muted">No documents yet.</td></tr>}
          </tbody>
        </table>
      </div>
    </div>
  );
}
