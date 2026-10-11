// Chat with the assistant: answers about complaints (function calling) and rules (RAG, with sources).
import { useEffect, useRef, useState } from "react";
import { api } from "../api.js";

const EXAMPLES = [
  "How many open complaints are there, by category?",
  "Show the 5 newest critical complaints",
  "What time do the hostel gates close?",
  "Where are the complaint hotspots this month?",
];

export default function Chat() {
  const [messages, setMessages] = useState([]);
  const [sessionId, setSessionId] = useState(null);
  const [text, setText] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const bottom = useRef(null);

  useEffect(() => bottom.current?.scrollIntoView({ behavior: "smooth" }), [messages]);

  async function send(question) {
    const message = (question ?? text).trim();
    if (message.length < 2 || busy) return;
    setMessages((m) => [...m, { role: "user", content: message }]);
    setText("");
    setBusy(true);
    setError("");
    try {
      const reply = await api("/chat/", { method: "POST", body: { message, session_id: sessionId } });
      setSessionId(reply.session_id);
      setMessages((m) => [...m, { role: "assistant", content: reply.answer, sources: reply.sources, tools: reply.tools_used, refused: reply.refused }]);
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  }

  function newConversation() {
    setMessages([]);
    setSessionId(null);
    setError("");
  }

  return (
    <div className="chat-page">
      <div className="page-head">
        <h1>Assistant</h1>
        <button className="button secondary" onClick={newConversation}>New conversation</button>
      </div>

      <div className="card chat-window" aria-live="polite">
        {messages.length === 0 && (
          <div className="muted">
            <p>Ask about complaints you can see, or about college rules. Try:</p>
            <div className="examples">
              {EXAMPLES.map((e) => <button key={e} className="chip" onClick={() => send(e)}>{e}</button>)}
            </div>
          </div>
        )}
        {messages.map((m, i) => (
          <div key={i} className={`bubble ${m.role} ${m.refused ? "refused" : ""}`}>
            <div className="bubble-text">{m.content}</div>
            {m.sources?.length > 0 && (
              <div className="sources small">
                Sources: {m.sources.map((s) => `${s.file}, page ${s.page}`).join(" · ")}
              </div>
            )}
            {m.tools?.length > 0 && <div className="muted small">Used: {[...new Set(m.tools)].join(", ")}</div>}
          </div>
        ))}
        {busy && <div className="bubble assistant muted">Thinking…</div>}
        <div ref={bottom} />
      </div>

      {error && <div className="alert error">{error}</div>}
      <form className="chat-input" onSubmit={(e) => { e.preventDefault(); send(); }}>
        <input value={text} onChange={(e) => setText(e.target.value)} placeholder="Ask a question…" maxLength={2000} aria-label="Question" />
        <button className="button" disabled={busy || text.trim().length < 2}>Send</button>
      </form>
    </div>
  );
}
