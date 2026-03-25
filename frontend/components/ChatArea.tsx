/** Chat area component with messages and input. */
'use client';

import { useState, useRef, useEffect } from 'react';
import { useChatStore } from '@/lib/store';
import { streamChat, getThreads, uploadPDF, getThreadDocument, getThreadMessages } from '@/lib/api-client';
import type { Message as MessageType } from '@/lib/types';
import Message from './Message';
import ToolStatus from './ToolStatus';

export default function ChatArea() {
  const {
    currentThreadId,
    messages,
    addMessage,
    setMessages,
    appendToLastAI,
    setActiveTool,
    isStreaming,
    setIsStreaming,
    setThreads,
    document,
    setDocument,
  } = useChatStore();

  const [input, setInput] = useState('');
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  // Auto-scroll to bottom
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  // Handle textarea auto-resize
  useEffect(() => {
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto';
      textareaRef.current.style.height = `${Math.min(textareaRef.current.scrollHeight, 200)}px`;
    }
  }, [input]);

  useEffect(() => {
    if (!currentThreadId) {
      setMessages([]);
      setDocument(null);
      return;
    }

    const threadId = currentThreadId;
    let cancelled = false;

    async function loadThreadState() {
      try {
        const [history, doc] = await Promise.all([
          getThreadMessages(threadId),
          getThreadDocument(threadId).catch(() => ({ has_document: false })),
        ]);

        if (!cancelled) {
          setMessages(history.messages);
          setDocument(doc);
        }
      } catch {
        if (!cancelled) {
          setMessages([]);
          setDocument(null);
        }
      }
    }

    loadThreadState();

    return () => {
      cancelled = true;
    };
  }, [currentThreadId, setDocument, setMessages]);

  async function handleSubmit(e?: React.FormEvent) {
    e?.preventDefault();
    if (!input.trim() || !currentThreadId || isStreaming) return;

    const userMessage = input.trim();
    setInput('');

    addMessage({
      id: Date.now().toString(),
      type: 'user',
      content: userMessage,
    });

    setIsStreaming(true);

    try {
      const generator = streamChat(userMessage, currentThreadId);

      for await (const event of generator) {
        if (event.type === 'ai' && event.content) {
          const existingMessages = useChatStore.getState().messages;
          if (existingMessages.length > 0 && existingMessages[existingMessages.length - 1].type === 'ai') {
            appendToLastAI(event.content);
          } else {
            addMessage({
              id: Date.now().toString(),
              type: 'ai',
              content: event.content,
            });
          }
        } else if (event.type === 'tool_call' && event.tool_name) {
          setActiveTool(event.tool_name);
          addMessage({
            id: Date.now().toString(),
            type: 'tool_call',
            content: '',
            toolName: event.tool_name,
          });
        } else if (event.type === 'tool' && event.tool_name) {
          setActiveTool(null);
          addMessage({
            id: Date.now().toString(),
            type: 'tool',
            content: typeof event.tool_result === 'string' ? event.tool_result : JSON.stringify(event.tool_result, null, 2),
            toolName: event.tool_name,
          });
        } else if (event.type === 'error') {
          addMessage({
            id: Date.now().toString(),
            type: 'ai',
            content: `Error: ${event.error}`,
          });
        }
      }
    } catch (err) {
      addMessage({
        id: Date.now().toString(),
        type: 'ai',
        content: `Error: ${err instanceof Error ? err.message : 'An error occurred'}`,
      });
    } finally {
      setIsStreaming(false);
      setActiveTool(null);
    }

    getThreads().then(setThreads).catch(() => { });
  }

  async function handleFileUpload(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    if (!file || !currentThreadId) return;

    try {
      const result = await uploadPDF(currentThreadId, file);
      const doc = await getThreadDocument(currentThreadId);
      setDocument(doc);

      addMessage({
        id: Date.now().toString(),
        type: 'ai',
        content: `I've successfully indexed \`${result.filename}\`. You can now ask questions about it!`,
      });
    } catch (err) {
      addMessage({
        id: `upload-error-${Date.now()}`,
        type: 'ai',
        content: `Upload failed: ${err instanceof Error ? err.message : 'Unknown error'}`,
      });
    } finally {
      e.target.value = '';
    }
  }

  return (
    <div className="flex-1 flex flex-col h-screen bg-background">
      {/* Header */}
      <header className="sticky top-0 z-10 flex items-center justify-between p-3 border-b border-border bg-background/80 backdrop-blur-md px-6">
        <div className="flex items-center gap-2">
          <span className="font-semibold text-sm">LangGraph AI</span>
          {document?.has_document && (
            <div className="flex items-center gap-1.5 px-2 py-0.5 bg-gray-800 rounded-full text-[10px] text-gray-400 border border-gray-700">
              <span className="w-1.5 h-1.5 rounded-full bg-accent animate-pulse" />
              {document.filename}
            </div>
          )}
        </div>
      </header>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto scroll-smooth">
        {!currentThreadId ? (
          <div className="flex flex-col items-center justify-center h-full text-center p-8">
            <h2 className="text-2xl font-bold mb-2">How can I help you today?</h2>
            <p className="text-gray-500 text-sm">Select a conversation or start a new one.</p>
          </div>
        ) : (
          <div className="pt-4 pb-12 w-full">
            {messages.map((msg: MessageType) => (
              <Message key={msg.id} message={msg} />
            ))}
            <div className="max-w-3xl mx-auto px-4 md:px-6 lg:px-8">
              <ToolStatus />
            </div>
            <div ref={messagesEndRef} />
          </div>
        )}
      </div>

      {/* Input BAR */}
      <div className="w-full max-w-3xl mx-auto p-4 pb-8">
        <div className="relative flex flex-col w-full bg-sidebar-bg border border-border rounded-2xl p-1 shadow-sm focus-within:border-gray-500 transition-colors">
          <textarea
            ref={textareaRef}
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                handleSubmit();
              }
            }}
            placeholder="Message LangGraph AI..."
            disabled={!currentThreadId || isStreaming}
            className="w-full px-4 py-3 bg-transparent border-none outline-none text-[15px] resize-none chat-input-textarea placeholder-gray-500"
            rows={1}
          />

          <div className="flex items-center justify-between px-2 pb-1">
            <div className="flex gap-1">
              <button
                onClick={() => fileInputRef.current?.click()}
                disabled={!currentThreadId || isStreaming}
                className="p-2 text-gray-500 hover:text-foreground hover:bg-sidebar-hover rounded-lg transition-colors disabled:opacity-30"
                title="Attach PDF"
              >
                <svg className="w-5 h-5" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <path strokeLinecap="round" strokeLinejoin="round" d="M18.375 12.739l-7.693 7.693a4.5 4.5 0 01-6.364-6.364l10.94-10.94A3 3 0 1119.5 7.5L8.55 18.45a1.5 1.5 0 11-2.122-2.122L16.485 6.28" />
                </svg>
              </button>
              <input
                ref={fileInputRef}
                type="file"
                accept=".pdf"
                onChange={handleFileUpload}
                className="hidden"
              />
            </div>

            <button
              onClick={() => handleSubmit()}
              disabled={!currentThreadId || isStreaming || !input.trim()}
              className="p-2 transition-all rounded-lg disabled:opacity-20 bg-accent text-white hover:opacity-90 active:scale-95"
            >
              <svg className="w-5 h-5" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
                <path strokeLinecap="round" strokeLinejoin="round" d="M4.5 10.5L12 3m0 0l7.5 7.5M12 3v18" />
              </svg>
            </button>
          </div>
        </div>
        <div className="mt-2 text-[10px] text-center text-gray-500">
          AI can make mistakes. Verify important info.
        </div>
      </div>
    </div>
  );
}
