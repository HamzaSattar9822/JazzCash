import { useApp } from '../lib/AppContext';

export function DevPanel() {
  const { devMode, lastDebug } = useApp();
  if (!devMode) return null;

  const latency = (lastDebug.latency || {}) as Record<string, number | undefined>;
  const retrieved = (lastDebug.retrieved || []) as Array<{ title: string; score: number }>;

  return (
    <div className="dev-panel" aria-live="polite">
      <div>
        <strong>DEV MODE</strong>
      </div>
      <div>Language: {String(lastDebug.language || '—')}</div>
      <div>Intent: {String(lastDebug.intent || '—')}</div>
      <div>Agent: {String(lastDebug.agentState || '—')}</div>
      <div>STT: {latency.stt_ms != null ? `${latency.stt_ms} ms` : '—'}</div>
      <div>
        LLM first token:{' '}
        {latency.llm_first_token_ms != null ? `${latency.llm_first_token_ms} ms` : '—'}
      </div>
      <div>LLM total: {latency.llm_total_ms != null ? `${latency.llm_total_ms} ms` : '—'}</div>
      <div>
        TTS first audio:{' '}
        {latency.tts_first_audio_ms != null ? `${latency.tts_first_audio_ms} ms` : '—'}
      </div>
      <div>
        First audio perceived:{' '}
        {latency.first_audio_perceived_ms != null
          ? `${latency.first_audio_perceived_ms} ms`
          : '—'}
      </div>
      <div>Total: {latency.total_ms != null ? `${latency.total_ms} ms` : '—'}</div>
      <div>
        Retrieved:{' '}
        {retrieved.length
          ? retrieved.map((r) => `${r.title} (${r.score})`).join(', ')
          : '—'}
      </div>
    </div>
  );
}

export function DevToggle() {
  const { devMode, setDevMode } = useApp();
  return (
    <button
      type="button"
      className="dev-toggle"
      title="Toggle developer mode"
      onClick={() => setDevMode(!devMode)}
      aria-label="Toggle developer mode"
    >
      {devMode ? '◉' : '◎'}
    </button>
  );
}
