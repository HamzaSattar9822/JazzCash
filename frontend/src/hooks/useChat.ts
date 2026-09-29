import { useCallback, useEffect, useRef, useState } from 'react';
import { api, type AgentResponse, type ChatMessage, type LatencyMetrics } from '../lib/api';

export interface UiMessage {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  action?: AgentResponse['suggested_action'];
  language?: string;
  streaming?: boolean;
}

export function useChat(sessionId: string | null, setSessionId: (id: string) => void) {
  const [messages, setMessages] = useState<UiMessage[]>([]);
  const [loading, setLoading] = useState(false);
  const [prompts, setPrompts] = useState<string[]>([
    'Find a service',
    'How do I pay a bill?',
    'What is Raast?',
    'Show savings options',
    'Why did my payment fail?',
  ]);
  const [debug, setDebug] = useState<{
    language?: string;
    intent?: string;
    retrieved?: AgentResponse['retrieved'];
    latency?: LatencyMetrics;
    agentState?: string;
  }>({});

  const send = useCallback(
    async (text: string) => {
      const trimmed = text.trim();
      if (!trimmed || loading) return;

      const userMsg: UiMessage = {
        id: `u-${Date.now()}`,
        role: 'user',
        content: trimmed,
      };
      setMessages((m) => [...m, userMsg]);
      setLoading(true);
      setDebug((d) => ({ ...d, agentState: 'processing' }));

      const history: ChatMessage[] = [...messages, userMsg].map((m) => ({
        role: m.role,
        content: m.content,
      }));

      try {
        const res = await api.chat({
          message: trimmed,
          session_id: sessionId || undefined,
          history,
        });
        setSessionId(res.session_id);
        setMessages((m) => [
          ...m,
          {
            id: `a-${Date.now()}`,
            role: 'assistant',
            content: res.response,
            action: res.suggested_action,
            language: res.language,
          },
        ]);
        if (res.suggested_prompts?.length) setPrompts(res.suggested_prompts);
        setDebug({
          language: res.language,
          intent: res.intent,
          retrieved: res.retrieved,
          latency: res.latency,
          agentState: 'idle',
        });
      } catch (err) {
        const msg = err instanceof Error ? err.message : 'Network error';
        setMessages((m) => [
          ...m,
          {
            id: `e-${Date.now()}`,
            role: 'assistant',
            content: `Sorry — ${msg}. Check that the backend is running and LLM_API_KEY is set.`,
          },
        ]);
        setDebug((d) => ({ ...d, agentState: 'error' }));
      } finally {
        setLoading(false);
      }
    },
    [loading, messages, sessionId, setSessionId],
  );

  return { messages, loading, prompts, debug, send, setMessages };
}

export type VoiceUiState = 'idle' | 'listening' | 'processing' | 'speaking' | 'error';

export function useVoiceAssistant(
  sessionId: string | null,
  setSessionId: (id: string) => void,
) {
  const [state, setState] = useState<VoiceUiState>('idle');
  const [transcript, setTranscript] = useState('');
  const [reply, setReply] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [levels, setLevels] = useState<number[]>(Array(16).fill(4));
  const [debug, setDebug] = useState<LatencyMetrics & { language?: string; intent?: string }>({});

  const mediaRecorder = useRef<MediaRecorder | null>(null);
  const chunks = useRef<Blob[]>([]);
  const audioEl = useRef<HTMLAudioElement | null>(null);
  const audioCtx = useRef<AudioContext | null>(null);
  const analyser = useRef<AnalyserNode | null>(null);
  const raf = useRef<number>(0);
  const streamRef = useRef<MediaStream | null>(null);
  const pipelineStart = useRef<number>(0);

  const stopMeter = () => {
    if (raf.current) cancelAnimationFrame(raf.current);
    raf.current = 0;
  };

  const startMeter = (stream: MediaStream) => {
    stopMeter();
    audioCtx.current = new AudioContext();
    const source = audioCtx.current.createMediaStreamSource(stream);
    analyser.current = audioCtx.current.createAnalyser();
    analyser.current.fftSize = 64;
    source.connect(analyser.current);
    const data = new Uint8Array(analyser.current.frequencyBinCount);

    const tick = () => {
      if (!analyser.current) return;
      analyser.current.getByteFrequencyData(data);
      const bars = Array.from({ length: 16 }, (_, i) => {
        const v = data[i] || 0;
        return Math.max(4, Math.min(32, (v / 255) * 32));
      });
      setLevels(bars);
      raf.current = requestAnimationFrame(tick);
    };
    tick();
  };

  const stopPlayback = useCallback(() => {
    if (audioEl.current) {
      audioEl.current.pause();
      audioEl.current.src = '';
      audioEl.current = null;
    }
  }, []);

  const bargeIn = useCallback(() => {
    stopPlayback();
    if (state === 'speaking') setState('idle');
  }, [state, stopPlayback]);

  const ensureSession = async () => {
    if (sessionId) return sessionId;
    const s = await api.voiceSession();
    setSessionId(s.session_id);
    return s.session_id;
  };

  const processAudio = async (blob: Blob) => {
    setState('processing');
    setError(null);
    const sttStart = performance.now();
    try {
      const sid = await ensureSession();
      const { text, latency_ms } = await api.transcribe(sid, blob);
      setTranscript(text);
      if (!text.trim()) {
        setError('No speech detected. Try again.');
        setState('error');
        return;
      }

      const agent = await api.voiceRespond({ session_id: sid, transcript: text });
      setSessionId(agent.session_id);
      setReply(agent.response);

      setState('speaking');
      const ttsStart = performance.now();
      const { blob: audioBlob, latencyHeader, firstByteMs } = await api.speak(
        agent.response,
        agent.language,
      );
      const ttsClient = performance.now() - ttsStart;
      const url = URL.createObjectURL(audioBlob);
      const audio = new Audio(url);
      audioEl.current = audio;

      const firstAudio = performance.now() - pipelineStart.current;
      setDebug({
        ...agent.latency,
        stt_ms: latency_ms,
        tts_first_audio_ms: firstByteMs ?? (Number(latencyHeader) || ttsClient),
        first_audio_perceived_ms: Math.round(firstAudio),
        language: agent.language,
        intent: agent.intent,
      });

      await new Promise<void>((resolve, reject) => {
        audio.onended = () => resolve();
        audio.onerror = () => reject(new Error('Playback failed'));
        audio.play().catch(reject);
      });
      setState('idle');
    } catch (err) {
      const msg = err instanceof Error ? err.message : 'Voice pipeline error';
      setError(msg);
      setState('error');
    } finally {
      stopMeter();
    }
  };

  const startListening = async () => {
    try {
      stopPlayback();
      setError(null);
      setTranscript('');
      setReply('');
      pipelineStart.current = performance.now();

      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      streamRef.current = stream;
      startMeter(stream);

      const mime = MediaRecorder.isTypeSupported('audio/webm;codecs=opus')
        ? 'audio/webm;codecs=opus'
        : 'audio/webm';
      const recorder = new MediaRecorder(stream, { mimeType: mime });
      chunks.current = [];
      recorder.ondataavailable = (e) => {
        if (e.data.size) chunks.current.push(e.data);
      };
      recorder.onstop = () => {
        stream.getTracks().forEach((t) => t.stop());
        streamRef.current = null;
        const blob = new Blob(chunks.current, { type: mime });
        void processAudio(blob);
      };
      mediaRecorder.current = recorder;
      recorder.start(100);
      setState('listening');
    } catch {
      setError('Microphone permission denied. Allow mic access and retry.');
      setState('error');
    }
  };

  const stopListening = () => {
    if (mediaRecorder.current && mediaRecorder.current.state !== 'inactive') {
      mediaRecorder.current.stop();
    }
    stopMeter();
  };

  const interruptAndListen = async () => {
    bargeIn();
    await startListening();
  };

  useEffect(() => {
    return () => {
      stopPlayback();
      stopMeter();
      streamRef.current?.getTracks().forEach((t) => t.stop());
    };
  }, [stopPlayback]);

  return {
    state,
    transcript,
    reply,
    error,
    levels,
    debug,
    startListening,
    stopListening,
    bargeIn,
    interruptAndListen,
  };
}
