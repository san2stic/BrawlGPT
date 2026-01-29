import { useState, useRef, useEffect } from 'react';
import { Player, ChatMessage } from '../types';
import { sendChatMessageStream } from '../services/api';
import './ChatInterface.css';

interface ChatInterfaceProps {
    player: Player | null;
}

export default function ChatInterface({ player }: ChatInterfaceProps) {
    const [isOpen, setIsOpen] = useState(false);
    const [messages, setMessages] = useState<ChatMessage[]>([]);
    const [inputValue, setInputValue] = useState('');
    const [isLoading, setIsLoading] = useState(false);
    const [streamingMessage, setStreamingMessage] = useState('');
    const messagesEndRef = useRef<HTMLDivElement>(null);

    const scrollToBottom = () => {
        messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
    };

    useEffect(() => {
        scrollToBottom();
    }, [messages, isOpen, streamingMessage]);

    const handleSend = async () => {
        if (!inputValue.trim() || isLoading) return;

        const userMessage: ChatMessage = { role: 'user', content: inputValue };
        setMessages(prev => [...prev, userMessage]);
        setInputValue('');
        setIsLoading(true);
        setStreamingMessage('');

        try {
            const history = [...messages, userMessage];

            await sendChatMessageStream(
                history,
                player,
                (chunk: string) => {
                    setStreamingMessage((prev) => prev + chunk);
                },
                () => {
                    setMessages((prev) => [
                        ...prev,
                        { role: 'assistant', content: streamingMessage },
                    ]);
                    setStreamingMessage('');
                    setIsLoading(false);
                },
                (_err: Error) => {
                    const errorMessage: ChatMessage = {
                        role: 'system',
                        content: 'Désolé, je rencontre des difficultés pour répondre. Veuillez réessayer plus tard.'
                    };
                    setMessages((prev) => [...prev, errorMessage]);
                    setStreamingMessage('');
                    setIsLoading(false);
                }
            );
        } catch (error) {
            console.error('Chat streaming error:', error);
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
                className={`chat-toggle-button ${isOpen ? 'chat-open' : ''}`}
            >
                {isOpen ? (
                    <svg className=\"chat-icon\" fill=\"none\" viewBox=\"0 0 24 24\" stroke=\"currentColor\">
                <path strokeLinecap=\"round\" strokeLinejoin=\"round\" strokeWidth={2} d=\"M6 18L18 6M6 6l12 12\" />
            </svg>
            ) : (
            <svg className=\"chat-icon\" fill=\"none\" viewBox=\"0 0 24 24\" stroke=\"currentColor\">
            <path strokeLinecap=\"round\" strokeLinejoin=\"round\" strokeWidth={2} d=\"M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z\" />
        </svg >
                )
}
            </button >

    {/* Chat Window */ }
    < div className = {`chat-window ${isOpen ? 'chat-visible' : 'chat-hidden'}`}>
        {/* Header */ }
        < div className =\"chat-header\">
            < div className =\"chat-avatar\">
                < svg className =\"chat-icon\" fill=\"none\" viewBox=\"0 0 24 24\" stroke=\"currentColor\">
                    < path strokeLinecap =\"round\" strokeLinejoin=\"round\" strokeWidth={2} d=\"M9.75 17L9 20l-1 1h8l-1-1-.75-3M3 13h18M5 17h14a2 2 0 002-2V5a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z\" />
                        </svg >
                    </div >
    <div className=\"chat-header-info\">
        < h3 > Coach BrawlGPT</h3 >
            <p>
                {player ? `En attente de joueur...` : 'En attente de joueur...'}
            </p>
                    </div >
                </div >

    {/* Messages */ }
    < div className =\"chat-messages\">
{
    messages.length === 0 && (
        <div className=\"chat-empty-state\">
            <p>👋 Bonjour! Je suis votre coach IA.</p >
                <p>Posez-moi des questions sur vos brawlers, vos stats ou des stratégies !</p>
                        </div >
                    )
}

{
    messages.map((msg, idx) => (
        <div
            key={idx}
            className={`message-wrapper message-${msg.role}`}
        >
            <div className=\"message-bubble\">
            {msg.content}
        </div>
                        </div >
                    ))
}
{
    isLoading && (
        <div className=\"message-wrapper message-assistant\">
            < div className =\"message-bubble\">
                < div className =\"chat-loading\">
                    < span className =\"chat-loading-dot\"></span>
                        < span className =\"chat-loading-dot\"></span>
                            < span className =\"chat-loading-dot\"></span>
                                </div >
                            </div >
                        </div >
                    )
}
<div ref={messagesEndRef} />
                </div >

    {/* Input */ }
    < div className =\"chat-input-container\">
        < div className =\"chat-input-wrapper\">
            < input
type =\"text\"
value = { inputValue }
onChange = {(e) => setInputValue(e.target.value)}
onKeyDown = { handleKeyPress }
placeholder =\"Posez votre question...\"
className =\"chat-input\"
disabled = { isLoading }
    />
    <button
        onClick={handleSend}
        disabled={!inputValue.trim() || isLoading}
        className=\"chat-send-button\"
            >
            <svg className=\"chat-send-icon\" fill=\"none\" viewBox=\"0 0 24 24\" stroke=\"currentColor\">
                < path strokeLinecap =\"round\" strokeLinejoin=\"round\" strokeWidth={2} d=\"M12 19l9 2-9-18-9 18 9-2zm0 0v-8\" />
                            </svg >
                        </button >
                    </div >
                </div >
            </div >
        </>
    );
}
