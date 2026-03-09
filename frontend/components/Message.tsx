/** Message component for displaying individual messages. */
import { Message } from '@/lib/types';

interface MessageProps {
  message: Message;
}

export default function Message({ message }: MessageProps) {
  const isUser = message.type === 'user';
  const isTool = message.type === 'tool';
  const isToolCall = message.type === 'tool_call';

  if (isToolCall) {
    return (
      <div className="flex justify-center mb-2">
        <div className="bg-amber-900/30 border border-amber-700 rounded-lg px-4 py-2 text-sm text-amber-200">
          <span className="font-medium">Calling tool:</span> {message.toolName}
        </div>
      </div>
    );
  }

  if (isTool) {
    return (
      <div className="flex justify-center mb-2">
        <div className="bg-purple-900/30 border border-purple-700 rounded-lg px-4 py-2 text-sm text-purple-200 max-w-[80%]">
          <div className="font-medium mb-1">Tool: {message.toolName}</div>
          <div className="text-purple-300 whitespace-pre-wrap">{message.content}</div>
        </div>
      </div>
    );
  }

  return (
    <div className={`flex mb-4 ${isUser ? 'justify-end' : 'justify-start'}`}>
      <div
        className={`max-w-[70%] rounded-lg px-4 py-2 ${
          isUser
            ? 'bg-blue-600 text-white'
            : 'bg-gray-800 text-gray-100'
        }`}
      >
        <div className="whitespace-pre-wrap break-words">{message.content}</div>
      </div>
    </div>
  );
}
