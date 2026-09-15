import { useEffect, useRef, useState } from 'react';
import { Link } from 'react-router-dom';
import { api } from '../services/api';
import type {
  AssistantAttentionItem,
  AssistantBriefing,
  AssistantReference,
  AssistantStreamEvent,
} from '../types';

interface ChatMessage {
  id: number;
  role: 'user' | 'assistant';
  text: string;
  references?: AssistantReference[];
  isError?: boolean;
  isTyping?: boolean;
  status?: string;
}

const exampleQuestions = [
  'Give me an overview of the project',
  'How much funding has been received?',
  'What is the total estimated amount?',
  'How much have we spent in expenses?',
  'Which activities are delayed?',
];

const TOOL_LABELS: Record<string, string> = {
  get_project_summary: 'the project overview',
  get_estimates: 'the estimate records',
  get_funding: 'the funding records',
  get_expenses: 'the expense records',
  get_resources: 'the resource records',
  get_schedule: 'the project schedule',
  get_delays: 'the delay tracking',
  get_record: 'the record detail',
};

const ATTENTION_LABELS: Record<string, string> = {
  funding: 'Funding',
  delays: 'Delays',
  milestones: 'Milestones',
  evidence: 'Evidence',
  expenses: 'Expenses',
};

const ATTENTION_COLORS: Record<string, string> = {
  funding: 'bg-amber-50 border-amber-200 text-amber-900',
  delays: 'bg-red-50 border-red-200 text-red-900',
  milestones: 'bg-indigo-50 border-indigo-200 text-indigo-900',
  evidence: 'bg-amber-50 border-amber-200 text-amber-900',
  expenses: 'bg-slate-50 border-slate-200 text-slate-800',
};

let messageId = 0;

const nextId = () => ++messageId;

function ReferenceLinks({ references }: { references: AssistantReference[] }) {
  if (!references.length) return null;
  return (
    <div className="mt-3 pt-3 border-t border-slate-200 space-y-1">
      {references.map((ref) => (
        <Link
          key={ref.entity_id}
          to={ref.href}
          className="flex items-center gap-2 text-blue-700 hover:text-blue-900 hover:underline text-sm"
        >
          <span>↳</span> {ref.label}
        </Link>
      ))}
    </div>
  );
}

function AttentionItem({ item }: { item: AssistantAttentionItem }) {
  const label = ATTENTION_LABELS[item.kind] ?? item.kind;
  const color = ATTENTION_COLORS[item.kind] ?? 'bg-slate-50 border-slate-200 text-slate-800';
  return (
    <div className={`rounded-lg border px-4 py-3 text-sm ${color}`}>
      <p className="flex items-center gap-2">
        <span className="inline-block w-2 h-2 rounded-full bg-current opacity-60" aria-hidden="true" />
        <span className="font-medium">{label}:</span> {item.message}
      </p>
      <ReferenceLinks references={item.references} />
    </div>
  );
}

export default function AskAssistant() {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState('');
  const [sending, setSending] = useState(false);
  const [briefing, setBriefing] = useState<AssistantBriefing | null>(null);
  const scrollRef = useRef<HTMLDivElement>(null);
  const formRef = useRef<HTMLFormElement>(null);

  useEffect(() => {
    let cancelled = false;
    api
      .getBriefing()
      .then((data) => {
        if (!cancelled) setBriefing(data);
      })
      .catch(() => {
        if (!cancelled) setBriefing(null);
      });
    return () => {
      cancelled = true;
    };
  }, []);

  useEffect(() => {
    const el = scrollRef.current;
    if (el) el.scrollTo({ top: el.scrollHeight, behavior: 'smooth' });
  }, [messages, sending]);

  const submit = async (question: string) => {
    const trimmed = question.trim();
    if (!trimmed || sending) return;

    const assistantId = nextId();
    setMessages((prev) => [
      ...prev,
      { id: nextId(), role: 'user', text: trimmed } satisfies ChatMessage,
      {
        id: assistantId,
        role: 'assistant',
        text: '',
        isTyping: true,
        status: 'Checking the project records…',
      } satisfies ChatMessage,
    ]);
    setInput('');
    setSending(true);
    formRef.current?.reset();

    const handleEvent = (event: AssistantStreamEvent) => {
      setMessages((prev) =>
        prev.map((message) => {
          if (message.id !== assistantId) return message;
          switch (event.type) {
            case 'status':
              return { ...message, status: event.text ?? message.status, isTyping: true };
            case 'tool':
              return {
                ...message,
                status: `Retrieved ${TOOL_LABELS[event.tool ?? ''] ?? event.tool}…`,
                isTyping: false,
              };
            case 'delta':
              return { ...message, text: message.text + (event.text ?? ''), isTyping: false };
            case 'done':
              return {
                ...message,
                text: event.text ?? message.text,
                references: event.references,
                isTyping: false,
                status: undefined,
              };
            case 'error':
              return {
                ...message,
                text: event.text ?? 'Something went wrong asking the assistant.',
                isError: true,
                isTyping: false,
                status: undefined,
              };
            default:
              return message;
          }
        })
      );
    };

    try {
      await api.askAssistantStream(trimmed, handleEvent);
    } catch (e) {
      const message = e instanceof Error ? e.message : 'Something went wrong asking the assistant.';
      setMessages((prev) =>
        prev.map((m) =>
          m.id === assistantId
            ? { ...m, text: message, isError: true, isTyping: false, status: undefined }
            : m
        )
      );
    } finally {
      setSending(false);
    }
  };

  const suggestions = briefing?.suggestions?.length ? briefing.suggestions : exampleQuestions;

  return (
    <div>
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-slate-900">Ask the Assistant</h1>
        <p className="mt-1 text-slate-500">
          A read-only companion that answers from the records you can already see. The assistant
          never changes data.
        </p>
      </div>

      {briefing && (
        <div className="mb-6 rounded-lg border border-blue-200 bg-blue-50 p-4">
          <p className="text-sm text-blue-900">{briefing.greeting}</p>
          {briefing.attention.length > 0 && (
            <div className="mt-3 space-y-2">
              {briefing.attention.map((item, index) => (
                <AttentionItem key={`${item.kind}-${index}`} item={item} />
              ))}
            </div>
          )}
        </div>
      )}

      <div className="bg-white rounded-lg border border-slate-200">
        <div
          ref={scrollRef}
          className="p-6 max-h-[28rem] overflow-y-auto space-y-4"
          aria-live="polite"
        >
          {messages.length === 0 && (
            <div>
              <p className="text-sm text-slate-500 mb-3">Try one of these, or ask your own question:</p>
              <div className="flex flex-wrap gap-2">
                {suggestions.map((question) => (
                  <button
                    key={question}
                    type="button"
                    disabled={sending}
                    onClick={() => submit(question)}
                    className="inline-flex items-center px-3 py-2 rounded-lg border border-slate-300 text-sm text-slate-700 hover:bg-slate-50 hover:text-slate-900 transition-colors disabled:opacity-50"
                  >
                    {question}
                  </button>
                ))}
              </div>
            </div>
          )}

          {messages.map((message) => (
            <div
              key={message.id}
              className={`flex ${message.role === 'user' ? 'justify-end' : 'justify-start'}`}
            >
              <div
                className={`max-w-[85%] rounded-lg px-4 py-3 text-sm whitespace-pre-line ${
                  message.role === 'user'
                    ? 'bg-blue-800 text-white'
                    : message.isError
                      ? 'bg-red-50 border border-red-200 text-red-800'
                      : 'bg-slate-50 border border-slate-200 text-slate-800'
                }`}
              >
                {message.isTyping && !message.text ? (
                  <p className="text-slate-400">{message.status ?? 'Thinking…'}</p>
                ) : (
                  <>
                    <p>
                      {message.text}
                      {message.isTyping && <span>▍</span>}
                    </p>
                    <ReferenceLinks references={message.references ?? []} />
                  </>
                )}
              </div>
            </div>
          ))}
        </div>

        <form
          ref={formRef}
          className="border-t border-slate-200 p-4 flex gap-3"
          onSubmit={(e) => {
            e.preventDefault();
            submit(input);
          }}
        >
          <label className="sr-only" htmlFor="assistant-question">
            Your question
          </label>
          <input
            id="assistant-question"
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder="Ask about estimates, funding, expenses, resources, delays…"
            className="flex-1 rounded-lg border border-slate-300 px-4 py-2 text-sm text-slate-900 placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-blue-800 focus:border-transparent"
            disabled={sending}
          />
          <button
            type="submit"
            disabled={sending || !input.trim()}
            className="inline-flex items-center px-4 py-2 bg-blue-800 text-white rounded-lg text-sm font-medium hover:bg-blue-900 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
          >
            Ask
          </button>
        </form>
      </div>
    </div>
  );
}