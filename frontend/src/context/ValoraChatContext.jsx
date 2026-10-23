import { createContext, useContext, useEffect, useState } from 'react';
import { streamAskValora } from '../lib/intelligence';

const ValoraChatContext = createContext(null);

export function ValoraChatProvider({ children }) {
  const [messages, setMessages] = useState([]);
  const [streaming, setStreaming] = useState(false);
  const [error, setError] = useState(null);
  const [spotlightOpen, setSpotlightOpen] = useState(false);

  // Global Cmd+K / Ctrl+K keyboard shortcut
  useEffect(() => {
    function handleKeyDown(e) {
      if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === 'k') {
        e.preventDefault();
        setSpotlightOpen((prev) => !prev);
      } else if (e.key === 'Escape' && spotlightOpen) {
        setSpotlightOpen(false);
      }
    }
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [spotlightOpen]);

  async function sendQuestion(questionText, { estateId, role }) {
    const q = (questionText || '').trim();
    if (!q || streaming) return;

    if (!estateId) {
      setError('Please select an active estate first.');
      return;
    }

    // Append user message
    const userMsgId = Date.now();
    const assistantMsgId = userMsgId + 1;
    const userMsg = {
      id: userMsgId,
      role: 'user',
      content: q,
      timestamp: new Date().toISOString(),
    };

    const currentHistory = [...messages];
    setMessages((prev) => [
      ...prev,
      userMsg,
      {
        id: assistantMsgId,
        role: 'assistant',
        content: '',
        timestamp: new Date().toISOString(),
        streaming: true,
      },
    ]);

    setStreaming(true);
    setError(null);

    try {
      await streamAskValora(
        q,
        { estateId, role },
        {
          onToken: (token) => {
            setMessages((prev) =>
              prev.map((msg) =>
                msg.id === assistantMsgId ? { ...msg, content: msg.content + token } : msg
              )
            );
          },
          onDone: () => {
            setStreaming(false);
            setMessages((prev) =>
              prev.map((msg) => (msg.id === assistantMsgId ? { ...msg, streaming: false } : msg))
            );
          },
          onError: (err) => {
            setStreaming(false);
            const errMsg =
              typeof err === 'string'
                ? err
                : err?.message || 'Unable to connect to VALORA Intelligence.';
            setError(errMsg);
            setMessages((prev) =>
              prev.map((msg) =>
                msg.id === assistantMsgId
                  ? {
                      ...msg,
                      content:
                        msg.content ||
                        'VALORA Intelligence was unable to complete this response. Please try again.',
                      streaming: false,
                    }
                  : msg
              )
            );
          },
        },
        currentHistory
      );
    } catch (err) {
      setStreaming(false);
      const errMsg =
        typeof err === 'string' ? err : err?.message || 'Failed to communicate with VALORA API.';
      setError(errMsg);
    }
  }

  function clearMessages() {
    setMessages([]);
    setError(null);
  }

  function openWithPrompt(promptText, context) {
    setSpotlightOpen(true);
    if (promptText) {
      sendQuestion(promptText, context);
    }
  }

  const value = {
    messages,
    streaming,
    error,
    setError,
    spotlightOpen,
    setSpotlightOpen,
    sendQuestion,
    clearMessages,
    openWithPrompt,
  };

  return <ValoraChatContext.Provider value={value}>{children}</ValoraChatContext.Provider>;
}

export function useValoraChat() {
  const ctx = useContext(ValoraChatContext);
  if (!ctx) {
    throw new Error('useValoraChat must be used within a ValoraChatProvider');
  }
  return ctx;
}
