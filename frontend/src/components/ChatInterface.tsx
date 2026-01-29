import { useState, useRef, useEffect } from 'react';
import { Player, ChatMessage } from '../types';
import { sendChatMessage } from '../services/api';

interface ChatInterfaceProps {
    player: Player | null;
}

export default function ChatInterface({ player }: ChatInterfaceProps) {
    const [isOpen, setIsOpen] = useState(false);
    const [messages, setMessages] = useState<ChatMessage[]>([]);
    const [inputValue, setInputValue] = useState('');
    const [isLoading, setIsLoading] = useState(false);
    const messagesEndRef = useRef<HTMLDivElement>(null);

    const scrollToBottom = () => {
        messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
    };

    useEffect(() => {
        scrollToBottom();
    }, [messages, isOpen]);

    const handleSend = async () => {
        if (!inputValue.trim() || isLoading) return;

        const userMessage: ChatMessage = { role: 'user', content: inputValue };
        setMessages(prev => [...prev, userMessage]);
        setInputValue('');
        setIsLoading(true);

        try {
            // Include chat history except the last one added manually to avoid duplication if we were sending whole list logic
            // Actually we send the whole history including the new message
            const history = [...messages, userMessage];
            const response = await sendChatMessage(history, player);

            const botMessage: ChatMessage = { role: 'assistant', content: response };
            setMessages(prev => [...prev, botMessage]);
        } catch (error) {
            const errorMessage: ChatMessage = {
                role: 'system',
                content: 'Désolé, je rencontre des difficultés pour répondre. Veuillez réessayer plus tard.'
            };
            setMessages(prev => [...prev, errorMessage]);
        } finally {
            setIsLoading(false);
        }
    };

    const handleKeyPress = (e: React.KeyboardEvent) => {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            handleSend();
        }
    };

    return (
        <>
            {/* Floating Button */}
            <button
                onClick={() => setIsOpen(!isOpen)}
                className={`fixed bottom-6 right-6 p-4 rounded-full shadow-lg transition-all duration-300 z-50 ${isOpen
                        ? 'bg-slate-700 hover:bg-slate-600 rotate-90'
                        : 'bg-gradient-to-r from-yellow-400 to-orange-600 hover:scale-110 animate-bounce'
                    }`}
            >
                {isOpen ? (
                    <svg className="w-8 h-8 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                    </svg>
                ) : (
                    <svg className="w-8 h-8 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z" />
                    </svg>
                )}
            </button>

            {/* Chat Window */}
            <div
                className={`fixed bottom-24 right-6 w-96 max-w-[calc(100vw-3rem)] bg-slate-900 border border-slate-700 rounded-2xl shadow-2xl transition-all duration-300 z-50 flex flex-col overflow-hidden ${isOpen
                        ? 'opacity-100 translate-y-0 h-[600px] max-h-[calc(100vh-8rem)]'
                        : 'opacity-0 translate-y-10 h-0 pointer-events-none'
                    }`}
            >
                {/* Header */}
                <div className="p-4 bg-slate-800 border-b border-slate-700 flex items-center gap-3">
                    <div className="w-10 h-10 rounded-full bg-gradient-to-br from-yellow-400 to-orange-600 flex items-center justify-center">
                        <svg className="w-6 h-6 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9.75 17L9 20l-1 1h8l-1-1-.75-3M3 13h18M5 17h14a2 2 0 002-2V5a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z" />
                        </svg>
                    </div>
                    <div>
                        <h3 className="font-bold text-white">Coach BrawlGPT</h3>
                        <p className="text-xs text-slate-400">
                            {player ? `Connecté avec ${player.name}` : 'En attente de joueur...'}
                        </p>
                    </div>
                </div>

                {/* Messages */}
                <div className="flex-1 overflow-y-auto p-4 space-y-4 bg-slate-900/50">
                    {messages.length === 0 && (
                        <div className="text-center text-slate-500 mt-8">
                            <p>👋 Bonjour ! Je suis votre coach IA.</p>
                            <p className="text-sm mt-2">Posez-moi des questions sur vos brawlers, vos stats ou des stratégies !</p>
                        </div>
                    )}

                    {messages.map((msg, idx) => (
                        <div
                            key={idx}
                            className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}
                        >
                            <div
                                className={`max-w-[80%] p-3 rounded-2xl text-sm ${msg.role === 'user'
                                        ? 'bg-blue-600 text-white rounded-br-none'
                                        : msg.role === 'system'
                                            ? 'bg-red-500/20 text-red-200 border border-red-500/30'
                                            : 'bg-slate-700 text-slate-200 rounded-bl-none'
                                    }`}
                            >
                                <div className="whitespace-pre-wrap">{msg.content}</div>
                            </div>
                        </div>
                    ))}
                    {isLoading && (
                        <div className="flex justify-start">
                            <div className="bg-slate-700 text-slate-200 p-3 rounded-2xl rounded-bl-none">
                                <div className="flex gap-1">
                                    <span className="w-2 h-2 bg-slate-400 rounded-full animate-bounce"></span>
                                    <span className="w-2 h-2 bg-slate-400 rounded-full animate-bounce delay-100"></span>
                                    <span className="w-2 h-2 bg-slate-400 rounded-full animate-bounce delay-200"></span>
                                </div>
                            </div>
                        </div>
                    )}
                    <div ref={messagesEndRef} />
                </div>

                {/* Input */}
                <div className="p-4 bg-slate-800 border-t border-slate-700">
                    <div className="flex gap-2">
                        <input
                            type="text"
                            value={inputValue}
                            onChange={(e) => setInputValue(e.target.value)}
                            onKeyDown={handleKeyPress}
                            placeholder="Posez votre question..."
                            className="flex-1 bg-slate-900 border border-slate-600 rounded-xl px-4 py-2 text-white placeholder-slate-500 focus:outline-none focus:border-yellow-500 transition-colors"
                            disabled={isLoading}
                        />
                        <button
                            onClick={handleSend}
                            disabled={!inputValue.trim() || isLoading}
                            className="bg-gradient-to-r from-yellow-400 to-orange-600 p-2 rounded-xl text-white disabled:opacity-50 disabled:cursor-not-allowed hover:opacity-90 transition-opacity"
                        >
                            <svg className="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 19l9 2-9-18-9 18 9-2zm0 0v-8" />
                            </svg>
                        </button>
                    </div>
                </div>
            </div>
        </>
    );
}
