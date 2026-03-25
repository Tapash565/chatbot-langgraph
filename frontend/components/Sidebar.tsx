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
    setDocument,
  } = useChatStore();

  const [isCreating, setIsCreating] = useState(false);
  const [editingId, setEditingId] = useState<string | null>(null);
  const [editName, setEditName] = useState('');

  const loadThreads = useCallback(async () => {
    try {
      const threadList = await getThreads();
      if (threadList.length > 0) {
        setThreads(threadList);
        if (!currentThreadId) {
          setCurrentThreadId(threadList[0].id);
        }
      } else if (!currentThreadId && !isCreating) {
        const thread = await createThread('New Chat');
        setThreads([thread]);
        setCurrentThreadId(thread.id);
        clearMessages();
      }
    } catch (err) {
      console.error('Failed to load threads:', err);
    }
  }, [clearMessages, currentThreadId, isCreating, setCurrentThreadId, setThreads]);

  useEffect(() => {
    loadThreads();
  }, [loadThreads]);

  const handleCreateThread = useCallback(async () => {
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
  }, [addThread, clearMessages, setCurrentThreadId]);

  async function handleDeleteThread(e: React.MouseEvent, id: string) {
    e.stopPropagation();
    try {
      await deleteThread(id);
      removeThread(id);
      if (currentThreadId === id) {
        setCurrentThreadId(null);
        clearMessages();
        setDocument(null);
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
    <div className="w-64 h-screen bg-sidebar-bg border-r border-border flex flex-col text-foreground">
      <div className="p-3">
        <button
          onClick={handleCreateThread}
          disabled={isCreating}
          className="flex items-center gap-2 w-full p-3 rounded-lg hover:bg-sidebar-hover transition-colors text-sm font-medium border border-border"
        >
          <svg className="w-5 h-5 shrink-0" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <path strokeLinecap="round" strokeLinejoin="round" d="M12 4.5v15m7.5-7.5h-15" />
          </svg>
          <span className="truncate">{isCreating ? 'Creating...' : 'New chat'}</span>
        </button>
      </div>

      <div className="flex-1 overflow-y-auto px-3 pb-4">
        <div className="space-y-1">
          {threads.length > 0 && (
            <div className="px-2 py-4 text-xs font-semibold text-gray-500 uppercase tracking-wider">
              Recent Chats
            </div>
          )}
          {threads.map((thread: Thread) => (
            <div
              key={thread.id}
              onClick={() => {
                setCurrentThreadId(thread.id);
              }}
              className={`group relative flex items-center gap-2 p-3 rounded-lg cursor-pointer transition-colors text-sm ${currentThreadId === thread.id
                  ? 'bg-sidebar-hover'
                  : 'hover:bg-sidebar-hover'
                }`}
            >
              <svg className="w-4 h-4 text-gray-400 shrink-0" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <path strokeLinecap="round" strokeLinejoin="round" d="M7.5 8.25h9m-9 3H12m-9.75 1.51c0 1.6 1.123 2.994 2.707 3.227 1.129.166 2.27.293 3.423.379.35.026.67.21.865.501L12 21l2.755-4.133a1.14 1.14 0 01.865-.501 48.172 48.172 0 003.423-.379c1.584-.233 2.707-1.626 2.707-3.228V6.741c0-1.602-1.123-2.995-2.707-3.228A48.394 48.394 0 0012 3c-2.392 0-4.744.175-7.043.513C3.373 3.746 2.25 5.14 2.25 6.741v6.018z" />
              </svg>

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
                  className="flex-1 bg-transparent border-none outline-none p-0 text-sm"
                  autoFocus
                  onClick={(e) => e.stopPropagation()}
                />
              ) : (
                <>
                  <span className="truncate flex-1 pr-6">{thread.name || 'Untitled Chat'}</span>
                  <div className={`absolute right-2 flex items-center gap-1 opacity-0 group-hover:opacity-100 transition-opacity bg-transparent`}>
                    <button
                      onClick={(e) => {
                        e.stopPropagation();
                        handleStartRename(thread.id, thread.name);
                      }}
                      className="p-1 hover:text-accent"
                      title="Rename"
                    >
                      <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15.232 5.232l3.536 3.536m-2.036-5.036a2.5 2.5 0 113.536 3.536L6.5 21.036H3v-3.572L16.732 3.732z" />
                      </svg>
                    </button>
                    <button
                      onClick={(e) => handleDeleteThread(e, thread.id)}
                      className="p-1 hover:text-red-500"
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
            <p className="text-gray-500 text-xs text-center p-4">No conversations yet</p>
          )}
        </div>
      </div>

      <div className="p-3 border-t border-border">
        <div className="flex items-center gap-3 p-2 rounded-lg hover:bg-sidebar-hover transition-colors cursor-pointer">
          <div className="w-8 h-8 rounded-full bg-accent flex items-center justify-center text-white text-xs font-bold">
            U
          </div>
          <div className="flex-1 truncate text-sm font-medium">
            User Account
          </div>
        </div>
      </div>
    </div>
  );
}
