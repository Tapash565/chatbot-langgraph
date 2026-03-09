/** Chat area component with messages and input. */
'use client';

import { useState, useRef, useEffect } from 'react';
import { useChatStore } from '@/lib/store';
import { streamChat, getThreads } from '@/lib/api-client';
import Message from './Message';
import ToolStatus from './ToolStatus';

export default function ChatArea() {
  const {
    currentThreadId,
    messages,
    addMessage,
    appendToLastAI,
    setActiveTool,
    isStreaming,
    setIsStreaming,
    setThreads,
  } = useChatStore();

  const [input, setInput] = useState('');
  const messagesEndRef = useRef<HTMLDivElement>(null);

  // Auto-scroll to bottom
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!input.trim() || !currentThreadId || isStreaming) return;

    const userMessage = input.trim();
    setInput('');

    // Add user message
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
          // Check if this is first AI message or continuation
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

    // Refresh thread list to get updated title (best-effort, errors silently ignored)
    getThreads().then(setThreads).catch(() => {});
  }

  return (
    <div className="flex-1 flex flex-col h-screen bg-gray-950">
      {/* Header */}
      <div className="p-4 border-b border-gray-800 bg-gray-900">
        <h1 className="text-xl font-semibold text-white">LangGraph Chatbot</h1>
      </div>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto p-4">
        {!currentThreadId ? (
          <div className="flex items-center justify-center h-full">
            <p className="text-gray-500">Select or create a chat to start</p>
          </div>
        ) : (
          <>
            {messages.map((msg) => (
              <Message key={msg.id} message={msg} />
            ))}
            <ToolStatus />
            <div ref={messagesEndRef} />
          </>
        )}
      </div>

      {/* Input */}
      <div className="p-4 border-t border-gray-800 bg-gray-900">
        <form onSubmit={handleSubmit} className="flex gap-2">
          <input
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder={currentThreadId ? 'Type your message...' : 'Select a chat first'}
            disabled={!currentThreadId || isStreaming}
            className="flex-1 px-4 py-3 bg-gray-800 border border-gray-700 rounded-lg text-white placeholder-gray-500 focus:outline-none focus:border-blue-500 disabled:opacity-50"
          />
          <button
            type="submit"
            disabled={!currentThreadId || isStreaming || !input.trim()}
            className="px-6 py-3 bg-blue-600 hover:bg-blue-700 text-white font-medium rounded-lg transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
          >
            Send
          </button>
        </form>
      </div>
    </div>
  );
}
