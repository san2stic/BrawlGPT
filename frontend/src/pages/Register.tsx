import React, { useState } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { Lock, Mail, ArrowRight, Loader2 } from 'lucide-react';
import './Auth.css';

// Using relative URLs - nginx routes /api/ to backend

export default function Register() {
    const [email, setEmail] = useState('');
    const [password, setPassword] = useState('');
    const [error, setError] = useState('');
    const [loading, setLoading] = useState(false);
    const navigate = useNavigate();

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        setError('');
        setLoading(true);

        try {
            const response = await fetch('/api/auth/register', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    email,
                    password,
                }),
            });

            if (!response.ok) {
                const data = await response.json();
                throw new Error(data.detail || 'Registration failed');
            }

            // Auto login after register? Or redirect to login. Let's redirect to login for now.
            navigate('/login');
        } catch (err: any) {
            setError(err.message);
        } finally {
            setLoading(false);
        }
    };

    return (
        <div className="auth-page">
            <div className="auth-background"></div>
            <div className="auth-background-blur">
                <div className="auth-blur-circle-1"></div>
                <div className="auth-blur-circle-2"></div>
            </div>

            <div className="auth-card">
                <div className="auth-header">
                    <h2 className="auth-title">Create Account</h2>
                    <p className="auth-subtitle">Join BrawlGPT for advanced insights</p>
                </div>

                {error && (<div className="auth-error">{error}</div>)}

                <form onSubmit={handleSubmit} className="auth-form">
                    <div className="auth-form-group">
                        <label className="auth-form-label">Email</label>
                        <div className="auth-input-wrapper">
                            <Mail className="auth-input-icon" size={20} />
                            <input
                                type="email"
                                required
                                value={email}
                                onChange={(e) => setEmail(e.target.value)}
                                className="auth-input"
                                placeholder="name@example.com"
                            />
                        </div>
                    </div>

                    <div className="auth-form-group">
                        <label className="auth-form-label">Password</label>
                        <div className="auth-input-wrapper">
                            <Lock className="auth-input-icon" size={20} />
                            <input
                                type="password"
                                required
                                value={password}
                                onChange={(e) => setPassword(e.target.value)}
                                className="auth-input"
                                placeholder="••••••••"
                            />
                        </div>
                    </div>

                    <button
                        type="submit"
                        disabled={loading}
                        className="auth-submit-button"
                    >
                        {loading ? (
                            <Loader2 className="auth-submit-loading" size={20} />
                        ) : (
                            <>
                                Create Account
                                <ArrowRight size={20} />
                            </>
                        )}
                    </button>
                </form>

                <div className="auth-footer">
                    Already have an account?{' '}
                    <Link to="/login" className="auth-footer-link">
                        Sign in
                    </Link>
                </div>
            </div>
        </div>
    );
}
