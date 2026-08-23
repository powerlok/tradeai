import { MessageCircle, RotateCcw, Send, Sparkles, X } from 'lucide-react';
import { useEffect, useRef, useState } from 'react';
import { streamMarketChat } from '../api';

export type ChatMessage = {
  id: string;
  role: 'user' | 'assistant';
  text: string;
  error?: boolean;
};

function isRetryableError(text: string) {
  return /network error|failed to fetch|temporariamente indisponível|erro da api|não consegui consultar|provider de ia .* indisponível/i.test(text);
}

export function MarketChat({
  token,
  userId,
  symbol,
  timeframe,
  signal,
  lastPrice,
  spread,
  marketState,
  open,
  onToggle,
}: {
  token: string;
  userId: string;
  symbol: string;
  timeframe: string;
  signal?: string | null;
  lastPrice?: number | null;
  spread?: number | null;
  marketState?: string | null;
  open: boolean;
  onToggle: () => void;
}) {
  const storageKey = `trading_chat_history:${userId}`;
  const [messages, setMessages] = useState<ChatMessage[]>(() => {
    try {
      const saved = localStorage.getItem(storageKey);
      return saved ? (JSON.parse(saved) as ChatMessage[]).map((message) => ({ ...message, error: message.error || (message.role === 'assistant' && isRetryableError(message.text)) })) : [{ id: 'welcome', role: 'assistant', text: 'Pergunte sobre uma ou mais criptomoedas. Vou buscar os dados atuais de cada ativo e analisar tendência, sinal, risco, spread e volume.' }];
    } catch {
      return [{ id: 'welcome', role: 'assistant', text: 'Pergunte sobre uma ou mais criptomoedas. Vou buscar os dados atuais de cada ativo e analisar tendência, sinal, risco, spread e volume.' }];
    }
  });
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const [workingStatus, setWorkingStatus] = useState('');
  const threadRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    localStorage.setItem(storageKey, JSON.stringify(messages.slice(-100)));
  }, [messages, storageKey]);

  useEffect(() => {
    if (!open) return;
    const frame = window.requestAnimationFrame(() => {
      const thread = threadRef.current;
      if (thread) thread.scrollTo({ top: thread.scrollHeight, behavior: 'auto' });
    });
    return () => window.cancelAnimationFrame(frame);
  }, [messages, loading, workingStatus, open]);

  const safeSignal = signal ?? 'indisponível';
  const safeMarketState = marketState ?? 'sem contexto suficiente';

  async function sendQuestion(trimmed: string, retryFromIndex?: number) {
    if (!trimmed || loading) return;

    if (retryFromIndex !== undefined) {
      setMessages((current) => current.slice(0, retryFromIndex));
    }

    const userMessage: ChatMessage = { id: crypto.randomUUID(), role: 'user', text: trimmed };
    setMessages((current) => [...current, userMessage]);
    setInput('');
    setLoading(true);

    try {
      let assistantId = '';
      await streamMarketChat(token, {
        message: trimmed,
        symbol,
        timeframe,
        signal: safeSignal,
        last_price: lastPrice ?? null,
        spread: spread ?? null,
        market_state: safeMarketState,
      }, (event) => {
        if (event.type === 'status') setWorkingStatus(event.message ?? 'Analisando...');
        if (event.type === 'token') {
          if (!assistantId) {
            assistantId = crypto.randomUUID();
            setMessages((current) => [...current, { id: assistantId, role: 'assistant', text: '' }]);
          }
          setMessages((current) => current.map((message) => message.id === assistantId ? { ...message, text: message.text + (event.content ?? '') } : message));
        }
        if (event.type === 'error') throw new Error(event.message ?? 'Não consegui consultar o mercado agora.');
      });
    } catch (error) {
      setMessages((current) => [
        ...current,
        {
          id: crypto.randomUUID(),
          role: 'assistant',
          text: error instanceof Error ? error.message : 'Não consegui consultar o mercado agora.',
          error: true,
        },
      ]);
    } finally {
      setLoading(false);
      setWorkingStatus('');
    }
  }

  function handleSend() {
    const trimmed = input.trim();
    if (!trimmed || loading) return;
    setInput('');
    void sendQuestion(trimmed);
  }

  function handleRetry(index: number) {
    if (loading) return;
    const previousMessages = messages.slice(0, index);
    let userIndex = -1;
    for (let cursor = previousMessages.length - 1; cursor >= 0; cursor -= 1) {
      if (previousMessages[cursor].role === 'user') {
        userIndex = cursor;
        break;
      }
    }
    if (userIndex >= 0) void sendQuestion(messages[userIndex].text, userIndex);
  }

  return (
    <>
      <button type="button" className="chat-launcher" onClick={onToggle} title="Abrir assistente de mercado" aria-label="Abrir assistente de mercado">
        <MessageCircle size={20} />
      </button>

      {open && (
        <div className="chat-panel">
          <div className="chat-header">
            <div>
              <div className="chat-kicker">Market AI</div>
              <strong>Busca por ativo</strong>
            </div>
            <button type="button" className="chat-close" onClick={onToggle} aria-label="Fechar chat">
              <X size={16} />
            </button>
          </div>

          <div className="chat-context"><Sparkles size={14} /><span>Busca ao vivo por ativo, direto na Binance</span></div>

          <div className="chat-thread" ref={threadRef}>
            {messages.map((message, index) => (
              <div key={message.id} className={`chat-bubble ${message.role}${message.error ? ' error' : ''}`}>
                <span>{message.text}</span>
                {(message.error || (message.role === 'assistant' && isRetryableError(message.text))) && <button type="button" className="chat-retry" onClick={() => handleRetry(index)} disabled={loading} title="Refazer pergunta" aria-label="Refazer pergunta"><RotateCcw size={13} /></button>}
              </div>
            ))}
            {loading && <div className="chat-bubble assistant pending"><span className="chat-status-dot" />{workingStatus || 'Analisando o mercado...'}</div>}
          </div>

          <div className="chat-input-row">
            <input
              value={input}
              onChange={(event) => setInput(event.target.value)}
              onKeyDown={(event) => {
                if (event.key === 'Enter') handleSend();
              }}
              placeholder="Pergunte sobre tendência, risco, sinal ou spread..."
              aria-label="Mensagem para a IA do mercado"
            />
            <button type="button" className="chat-send" onClick={handleSend} disabled={loading || !input.trim()}>
              <Send size={16} />
            </button>
          </div>
        </div>
      )}
    </>
  );
}
