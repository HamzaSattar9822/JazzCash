/** API client — all LLM/STT/TTS keys stay on the backend. */

const API_BASE = import.meta.env.VITE_API_BASE || '';

export type Language = 'english' | 'urdu' | 'roman_urdu' | 'mixed';
export type Intent =
  | 'service_discovery'
  | 'app_navigation'
  | 'how_to'
  | 'product_discovery'
  | 'fees'
  | 'troubleshooting'
  | 'transaction_explanation'
  | 'offers'
  | 'faq'
  | 'support'
  | 'contextual_assistance'
  | 'transaction_execution_request'
  | 'greeting'
  | 'unknown';

export interface SuggestedAction {
  label: string;
  route: string;
  description?: string;
}

export interface LatencyMetrics {
  language_ms?: number;
  intent_ms?: number;
  retrieval_ms?: number;
  llm_first_token_ms?: number;
  llm_total_ms?: number;
  stt_ms?: number;
  tts_first_audio_ms?: number;
  tts_total_ms?: number;
  first_audio_perceived_ms?: number;
  total_ms?: number;
}

export interface RetrievedDocument {
  id: string;
  title: string;
  category: string;
  score: number;
  snippet: string;
}

export interface AgentResponse {
  language: Language;
  intent: Intent;
  response: string;
  suggested_action?: SuggestedAction | null;
  suggested_prompts: string[];
  retrieved: RetrievedDocument[];
  latency: LatencyMetrics;
  session_id: string;
  blocked_transaction: boolean;
}

export interface ChatMessage {
  role: 'user' | 'assistant' | 'system';
  content: string;
}

async function jsonFetch<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    ...init,
    headers: {
      'Content-Type': 'application/json',
      ...(init?.headers || {}),
    },
  });
  if (!res.ok) {
    const text = await res.text();
    throw new Error(text || res.statusText);
  }
  return res.json() as Promise<T>;
}

export const api = {
  health: () => jsonFetch<{ status: string; llm: boolean; stt: boolean; tts: boolean }>('/api/health'),
  user: () => jsonFetch<Record<string, unknown>>('/api/user'),
  services: () => jsonFetch<{ services: Service[] }>('/api/services'),
  offers: () => jsonFetch<{ offers: Offer[] }>('/api/offers'),
  products: () => jsonFetch<{ products: Product[] }>('/api/products'),
  transactions: () =>
    jsonFetch<{ user: User; transactions: Txn[] }>('/api/transactions'),
  support: () => jsonFetch<{ tickets: Ticket[] }>('/api/support'),

  chat: (body: {
    message: string;
    session_id?: string;
    history?: ChatMessage[];
    context?: Record<string, unknown>;
  }) =>
    jsonFetch<AgentResponse>('/api/chat', {
      method: 'POST',
      body: JSON.stringify(body),
    }),

  voiceSession: (session_id?: string) =>
    jsonFetch<{ session_id: string }>('/api/voice/session', {
      method: 'POST',
      body: JSON.stringify({ session_id }),
    }),

  voiceRespond: (body: {
    session_id: string;
    transcript: string;
    history?: ChatMessage[];
  }) =>
    jsonFetch<AgentResponse>('/api/voice/respond', {
      method: 'POST',
      body: JSON.stringify(body),
    }),

  async transcribe(sessionId: string, blob: Blob, languageHint?: string) {
    const form = new FormData();
    form.append('session_id', sessionId);
    form.append('file', blob, 'audio.webm');
    if (languageHint) form.append('language_hint', languageHint);
    const res = await fetch(`${API_BASE}/api/voice/transcribe`, {
      method: 'POST',
      body: form,
    });
    if (!res.ok) {
      const text = await res.text();
      throw new Error(text || 'Transcription failed');
    }
    return res.json() as Promise<{ text: string; latency_ms: number }>;
  },

  async speak(text: string, language?: Language): Promise<{ blob: Blob; latencyHeader?: string; firstByteMs?: number }> {
    const t0 = performance.now();
    const res = await fetch(`${API_BASE}/api/voice/speak`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ text, language }),
    });
    if (!res.ok) {
      const err = await res.text();
      throw new Error(err || 'TTS failed');
    }
    if (!res.body) {
      const blob = await res.blob();
      return { blob, latencyHeader: res.headers.get('X-TTS-Latency-Ms') || undefined };
    }
    const reader = res.body.getReader();
    const chunks: BlobPart[] = [];
    let firstByteMs: number | undefined;
    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      if (value?.byteLength) {
        if (firstByteMs === undefined) firstByteMs = performance.now() - t0;
        chunks.push(value);
      }
    }
    const blob = new Blob(chunks, { type: 'audio/mpeg' });
    return {
      blob,
      latencyHeader: res.headers.get('X-TTS-Latency-Ms') || undefined,
      firstByteMs,
    };
  },
};

export interface User {
  id: string;
  name: string;
  phone: string;
  wallet_balance: number;
  currency: string;
  environment: string;
}

export interface Service {
  id: string;
  name: string;
  name_ur: string;
  route: string;
  icon: string;
  category: string;
  description: string;
}

export interface Offer {
  id: string;
  title: string;
  description: string;
  category: string;
  valid_until: string;
  route: string;
}

export interface Product {
  id: string;
  name: string;
  category: string;
  route: string;
  description: string;
  apr?: string | null;
}

export interface Txn {
  id: string;
  type: string;
  title: string;
  amount: number;
  status: string;
  timestamp: string;
  counterparty: string;
  failure_reason?: string;
}

export interface Ticket {
  id: string;
  subject: string;
  status: string;
  created: string;
}
