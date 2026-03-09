/** Sidebar component showing thread list. */
'use client';

import { useState, useEffect, useCallback } from 'react';
import { useChatStore } from '@/lib/store';
import { getThreads, createThread, deleteThread, renameThread } from '@/lib/api-client';
import type { Thread } from '@/lib/types';

export default function Sidebar() {
  const {
    threads,
    setThreads,
    currentThreadId,
    setCurrentThreadId,
    addThread,
    removeThread,
    updateThreadName,
    clearMessages,
  } = useChatStore();

  const [isCreating, setIsCreating] = useState(false);
  const [editingId, setEditingId] = useState<string | null>(null);
  const [editName, setEditName] = useState('');

  const loadThreads = useCallback(async () => {
    try {
      const threadList = await getThreads();
      setThreads(threadList);
    } catch (err) {
      console.error('Failed to load threads:', err);
    }
  }, [setThreads]);

  useEffect(() => {
    loadThreads();
  }, [loadThreads]);

  const handleCreateThread = async () => {
    setIsCreating(true);
    try {
      const thread = await createThread('New Chat');
      addThread(thread);
      setCurrentThreadId(thread.id);
      clearMessages();
    } catch (err) {
      console.error('Failed to create thread:', err);
    }
    setIsCreating(false);
  }

  async function handleDeleteThread(e: React.MouseEvent, id: string) {
    e.stopPropagation();
    try {
      await deleteThread(id);
      removeThread(id);
      if (currentThreadId === id) {
        setCurrentThreadId(null);
        clearMessages();
      }
    } catch (err) {
      console.error('Failed to delete thread:', err);
    }
  }

  function handleStartRename(id: string, name: string) {
    setEditingId(id);
    setEditName(name);
  }

  async function handleRename(id: string) {
    if (!editName.trim()) return;
    try {
      await renameThread(id, editName.trim());
      updateThreadName(id, editName.trim());
    } catch (err) {
      console.error('Failed to rename thread:', err);
    }
    setEditingId(null);
  }

  return (
    <div className="w-64 h-screen bg-gray-900 text-white flex flex-col">
      <div className="p-4 border-b border-gray-700">
        <button
          onClick={handleCreateThread}
          disabled={isCreating}
          className="w-full py-2 px-4 bg-blue-600 hover:bg-blue-700 rounded-lg font-medium transition-colors disabled:opacity-50"
        >
          {isCreating ? 'Creating...' : '+ New Chat'}
        </button>
      </div>

      <div className="flex-1 overflow-y-auto p-2">
        {threads.map((thread: Thread) => (
          <div
            key={thread.id}
            onClick={() => {
              setCurrentThreadId(thread.id);
              clearMessages();
            }}
            className={`group flex items-center justify-between p-3 rounded-lg cursor-pointer mb-1 transition-colors ${
              currentThreadId === thread.id
                ? 'bg-blue-600'
                : 'hover:bg-gray-800'
            }`}
          >
            {editingId === thread.id ? (
              <input
                type="text"
                value={editName}
                onChange={(e) => setEditName(e.target.value)}
                onBlur={() => handleRename(thread.id)}
                onKeyDown={(e) => {
                  if (e.key === 'Enter') handleRename(thread.id);
                  if (e.key === 'Escape') setEditingId(null);
                }}
                className="flex-1 bg-gray-700 px-2 py-1 rounded text-sm outline-none"
                autoFocus
                onClick={(e) => e.stopPropagation()}
              />
            ) : (
              <>
                <span className="truncate flex-1">{thread.name || 'Untitled Chat'}</span>
                <div className="hidden group-hover:flex gap-1">
                  <button
                    onClick={(e) => {
                      e.stopPropagation();
                      handleStartRename(thread.id, thread.name);
                    }}
                    className="p-1 hover:bg-gray-600 rounded"
                    title="Rename"
                  >
                    <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15.232 5.232l3.536 3.536m-2.036-5.036a2.5 2.5 0 113.536 3.536L6.5 21.036H3v-3.572L16.732 3.732z" />
                    </svg>
                  </button>
                  <button
                    onClick={(e) => handleDeleteThread(e, thread.id)}
                    className="p-1 hover:bg-red-600 rounded"
                    title="Delete"
                  >
                    <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                    </svg>
                  </button>
                </div>
              </>
            )}
          </div>
        ))}

        {threads.length === 0 && (
          <p className="text-gray-500 text-center p-4">No conversations yet</p>
        )}
      </div>
    </div>
  );
}
