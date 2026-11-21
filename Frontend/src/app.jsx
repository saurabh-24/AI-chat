import { useState, useRef, useEffect } from "react";
import "./App.css";

const API_BASE = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";

function generateSessionId() {
  return "s-" + Math.random().toString(36).substring(2, 10);
}

const QUICK_PROMPTS = [
  "What is the capital of France?",
  "My name is Alex.",
  "Explain caching in one sentence.",
];

export default function App() {
  const [sessionId, setSessionId] = useState(() => generateSessionId());
  const [systemPrompt, setSystemPrompt] = useState("");
  const [showSystemPrompt, setShowSystemPrompt] = useState(false);
  const [input, setInput] = useState("");
  const [messages, setMessages] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const endRef = useRef(null);

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, loading, error]);

  function startNewSession() {
    setSessionId(generateSessionId());
    setMessages([]);
    setError(null);
  }

  async function sendMessage(e, overrideText = null) {
    if (e) e.preventDefault();
    const trimmed = (overrideText ?? input).trim();
    if (!trimmed || loading) return;

    setInput("");
    setError(null);
    setMessages((prev) => [...prev, { role: "user", content: trimmed }]);
    setLoading(true);

    try {
      const payload = { session_id: sessionId, message: trimmed };
      if (systemPrompt.trim()) {
        payload.system_prompt = systemPrompt.trim();
      }

      const res = await fetch(`${API_BASE}/chat`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });

      const data = await res.json();
      if (!res.ok) {
        const detail =
          typeof data.detail === "string"
            ? data.detail
            : JSON.stringify(data.detail || "Request failed");
        setError(`Error ${res.status}: ${detail}`);
        return;
      }

      setMessages((prev) => [
        ...prev,
        { role: "assistant", content: data.reply, metadata: data.metadata },
      ]);
    } catch {
      setError("Network error: unable to reach the backend.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="app-shell">
      <header className="app-header">
        <div className="brand">
          <h1>Resilient AI Chat</h1>
          <span className="session-pill">Session: {sessionId}</span>
        </div>
        <div className="header-actions">
          <button
            type="button"
            className="btn-secondary"
            onClick={() => setShowSystemPrompt((v) => !v)}
          >
            {showSystemPrompt ? "Hide Prompt" : "System Prompt"}
          </button>
          <button
            type="button"
            className="btn-secondary"
            onClick={startNewSession}
          >
            + New Session
          </button>
        </div>
      </header>

      {showSystemPrompt && (
        <div className="system-prompt-bar">
          <label htmlFor="sys-prompt">Session System Prompt (optional)</label>
          <input
            id="sys-prompt"
            data-testid="system-prompt-input"
            type="text"
            placeholder="e.g., Answer concisely in 1-2 sentences."
            value={systemPrompt}
            onChange={(e) => setSystemPrompt(e.target.value)}
          />
        </div>
      )}

      <main className="chat-window">
        {messages.length === 0 && !error && (
          <div className="empty-state">
            <h2>Start a conversation</h2>
            <p>
              Multi-turn memory, automatic key failover, and LiteLLM response
              caching with per-request token tracking.
            </p>
            <div className="quick-prompts">
              {QUICK_PROMPTS.map((q) => (
                <button
                  key={q}
                  type="button"
                  className="prompt-chip"
                  onClick={() => sendMessage(null, q)}
                >
                  {q}
                </button>
              ))}
            </div>
          </div>
        )}

        {messages.map((m, idx) =>
          m.role === "user" ? (
            <div key={idx} className="msg-row user">
              <div className="user-bubble">{m.content}</div>
            </div>
          ) : (
            <div key={idx} className="msg-row assistant">
              <div className="assistant-card" data-testid="assistant-message">
                <div className="assistant-text">{m.content}</div>
                {m.metadata && (
                  <div className="meta-bar">
                    <span
                      className={`meta-pill ${
                        m.metadata.resolution_source === "LLM_CACHE"
                          ? "cache"
                          : "live"
                      }`}
                    >
                      <span data-testid="meta-source">
                        {m.metadata.resolution_source}
                      </span>
                    </span>
                    <span className="meta-pill">
                      Model: <strong data-testid="meta-model">{m.metadata.model}</strong>
                    </span>
                    <span className="meta-pill">
                      Latency:{" "}
                      <strong data-testid="meta-latency">
                        {m.metadata.latency_ms} ms
                      </strong>
                    </span>
                    <span className="meta-pill">
                      In:{" "}
                      <strong data-testid="meta-input-tokens">
                        {m.metadata.input_tokens}
                      </strong>
                    </span>
                    <span className="meta-pill">
                      Out:{" "}
                      <strong data-testid="meta-output-tokens">
                        {m.metadata.output_tokens}
                      </strong>
                    </span>
                  </div>
                )}
              </div>
            </div>
          )
        )}

        {loading && (
          <div className="msg-row assistant">
            <div className="typing-indicator" aria-label="Loading">
              <span />
              <span />
              <span />
            </div>
          </div>
        )}

        {error && <div className="error-banner">{error}</div>}
        <div ref={endRef} />
      </main>

      <form className="input-bar" onSubmit={sendMessage}>
        <input
          data-testid="chat-input"
          type="text"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="Type a message..."
          disabled={loading}
        />
        <button
          data-testid="send-button"
          type="submit"
          className="send-btn"
          disabled={loading}
        >
          Send
        </button>
      </form>
    </div>
  );
}