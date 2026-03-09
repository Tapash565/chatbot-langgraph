/** Zustand store for chatbot state management. */
import { create } from 'zustand';
import { Message, Thread, DocumentMetadata } from './types';

interface ChatStore {
  // Current thread
  currentThreadId: string | null;
  setCurrentThreadId: (id: string | null) => void;

  // Thread list
  threads: Thread[];
  setThreads: (threads: Thread[]) => void;
  addThread: (thread: Thread) => void;
  removeThread: (id: string) => void;
  updateThreadName: (id: string, name: string) => void;

  // Messages
  messages: Message[];
  setMessages: (messages: Message[]) => void;
  addMessage: (message: Message) => void;
  clearMessages: () => void;
  appendToLastAI: (content: string) => void;

  // Tool status
  activeTool: string | null;
  setActiveTool: (tool: string | null) => void;

  // Loading states
  isLoading: boolean;
  setIsLoading: (loading: boolean) => void;

  // Document
  document: DocumentMetadata | null;
  setDocument: (doc: DocumentMetadata | null) => void;

  // Streaming
  isStreaming: boolean;
  setIsStreaming: (streaming: boolean) => void;
}

export const useChatStore = create<ChatStore>((set) => ({
  // Current thread
  currentThreadId: null,
  setCurrentThreadId: (id) => set({ currentThreadId: id }),

  // Thread list
  threads: [],
  setThreads: (threads) => set({ threads }),
  addThread: (thread) => set((state) => ({ threads: [thread, ...state.threads] })),
  removeThread: (id) => set((state) => ({
    threads: state.threads.filter((t) => t.id !== id)
  })),
  updateThreadName: (id, name) => set((state) => ({
    threads: state.threads.map((t) => t.id === id ? { ...t, name } : t)
  })),

  // Messages
  messages: [],
  setMessages: (messages) => set({ messages }),
  addMessage: (message) => set((state) => ({
    messages: [...state.messages, message]
  })),
  clearMessages: () => set({ messages: [] }),
  appendToLastAI: (content) => set((state) => {
    const messages = [...state.messages];
    const lastIndex = messages.length - 1;
    if (lastIndex >= 0 && messages[lastIndex].type === 'ai') {
      messages[lastIndex] = {
        ...messages[lastIndex],
        content: messages[lastIndex].content + content
      };
    }
    return { messages };
  }),

  // Tool status
  activeTool: null,
  setActiveTool: (tool) => set({ activeTool: tool }),

  // Loading states
  isLoading: false,
  setIsLoading: (loading) => set({ isLoading: loading }),

  // Document
  document: null,
  setDocument: (doc) => set({ document: doc }),

  // Streaming
  isStreaming: false,
  setIsStreaming: (streaming) => set({ isStreaming: streaming }),
}));
