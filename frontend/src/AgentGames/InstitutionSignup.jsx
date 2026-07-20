import React, { useEffect, useState } from 'react';
import { useSearchParams, useNavigate, Link } from 'react-router-dom';
import { useDispatch } from 'react-redux';
import { toast } from 'react-toastify';
import { setToken } from '../slices/authSlice';

const apiUrl = import.meta.env.VITE_AGENT_API_URL;

const TIER_LABELS = {
    club: 'Club & School',
    university: 'University & Large Cohort',
    teacher: 'Teacher',
    school: 'Whole School',
};

function InstitutionSignup() {
    const [searchParams] = useSearchParams();
    const navigate = useNavigate();
    const dispatch = useDispatch();
    const sessionId = searchParams.get('session_id');

    const [loading, setLoading] = useState(true);
    const [verifyError, setVerifyError] = useState(null);
    const [info, setInfo] = useState(null); // { email, tier, auto_renew, address, already_registered }

    const [name, setName] = useState('');
    const [contactPerson, setContactPerson] = useState('');
    const [address, setAddress] = useState('');
    const [password, setPassword] = useState('');
    const [confirm, setConfirm] = useState('');
    const [submitting, setSubmitting] = useState(false);

    // Verify the Stripe payment server-side before showing the form. The email
    // comes back from the verified session; it is displayed grayed out and is
    // never editable here.
    useEffect(() => {
        if (!sessionId) {
            setVerifyError('Missing checkout session. Please start from the pricing page.');
            setLoading(false);
            return;
        }
        let cancelled = false;
        (async () => {
            try {
                const res = await fetch(`${apiUrl}/payments/checkout/${sessionId}`);
                const json = await res.json();
                if (cancelled) return;
                if (!res.ok) {
                    setVerifyError(
                        json?.detail ||
                        'We could not verify your payment. If you were charged, contact support.'
                    );
                } else {
                    const data = json || {};
                    setInfo(data);
                    setAddress(data.address || '');
                }
            } catch (err) {
                if (!cancelled) setVerifyError('Could not reach the server. Please try again.');
            } finally {
                if (!cancelled) setLoading(false);
            }
        })();
        return () => {
            cancelled = true;
        };
    }, [sessionId]);

    const handleSubmit = async (e) => {
        e.preventDefault();
        if (password !== confirm) {
            toast.error('Passwords do not match');
            return;
        }
        if (password.length < 8) {
            toast.error('Password must be at least 8 characters');
            return;
        }
        setSubmitting(true);
        try {
            const res = await fetch(`${apiUrl}/payments/institution-signup`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    session_id: sessionId,
                    name,
                    contact_person: contactPerson,
                    address,
                    password,
                }),
            });
            const json = await res.json();
            if (!res.ok) {
                toast.error(json?.detail || 'Signup failed. Please try again.');
                return;
            }
            // Auto-login: the backend returns a token for the new institution,
            // so log straight in and land on the home page.
            const noun = info?.is_teacher ? 'Teacher account' : 'Institution';
            const token = json?.access_token;
            if (token) {
                dispatch(setToken(token));
                toast.success(`${noun} created — you are now logged in.`);
                navigate('/InstitutionHome');
            } else {
                toast.success(`${noun} created — you can now log in.`);
                navigate(info?.is_teacher ? '/Teacher' : '/Institution');
            }
        } catch (err) {
            toast.error('Could not reach the server. Please try again.');
        } finally {
            setSubmitting(false);
        }
    };

    const card = 'bg-white rounded-lg shadow-lg p-8 border border-ui-light';

    // Teacher-page purchases (tiers "teacher"/"school") become teacher
    // accounts; the backend flags the verified session so wording can match.
    const teacherPlan = !!info?.is_teacher;

    return (
        <div className="min-h-screen pt-16 bg-ui-lighter">
            <div className="w-full max-w-xl mx-auto px-4 py-12">
                <h1 className="text-3xl font-bold text-ui-dark mb-6 text-center">
                    {info
                        ? `Complete your ${teacherPlan ? 'teacher' : 'institution'} signup`
                        : 'Complete your signup'}
                </h1>

                {loading && (
                    <div className={`${card} text-center text-ui`}>Verifying your payment…</div>
                )}

                {!loading && verifyError && (
                    <div className={`${card} text-center`}>
                        <p className="text-red-600 mb-4">{verifyError}</p>
                        <Link to="/Institutions" className="text-primary underline">
                            Back to pricing
                        </Link>
                    </div>
                )}

                {!loading && info && info.already_registered && (
                    <div className={`${card} text-center`}>
                        <p className="text-ui mb-4">
                            An account has already been created for this payment.
                        </p>
                        <Link
                            to={teacherPlan ? '/Teacher' : '/Institution'}
                            className="text-primary underline"
                        >
                            {teacherPlan ? 'Go to teacher login' : 'Go to institution login'}
                        </Link>
                    </div>
                )}

                {!loading && info && !info.already_registered && (
                    <form onSubmit={handleSubmit} className={`${card} space-y-4`}>
                        {info.tier && (
                            <p className="text-sm text-ui">
                                Plan:{' '}
                                <span className="font-semibold text-ui-dark">
                                    {TIER_LABELS[info.tier] || info.tier}
                                </span>
                                {info.auto_renew ? ' — auto-renews yearly' : ' — 90-day pass'}
                            </p>
                        )}

                        <div>
                            <label className="block text-sm font-medium text-ui-dark mb-1">
                                Contact email
                            </label>
                            <input
                                type="email"
                                value={info.email || ''}
                                disabled
                                className="w-full border border-ui-light rounded px-3 py-2 bg-ui-lighter text-ui cursor-not-allowed"
                            />
                        </div>

                        <div>
                            <label className="block text-sm font-medium text-ui-dark mb-1">
                                {teacherPlan ? 'Account name' : 'Institution name'}
                            </label>
                            <input
                                type="text"
                                required
                                value={name}
                                onChange={(e) => setName(e.target.value)}
                                className="w-full border border-ui-light rounded px-3 py-2"
                            />
                            {teacherPlan && (
                                <p className="text-xs text-ui mt-1">
                                    Your login name — e.g. "Ms Chen — Northcote High".
                                    Students will see it on their classrooms.
                                </p>
                            )}
                        </div>

                        <div>
                            <label className="block text-sm font-medium text-ui-dark mb-1">
                                {teacherPlan ? 'Your name' : 'Contact person'}
                            </label>
                            <input
                                type="text"
                                required
                                value={contactPerson}
                                onChange={(e) => setContactPerson(e.target.value)}
                                className="w-full border border-ui-light rounded px-3 py-2"
                            />
                        </div>

                        <div>
                            <label className="block text-sm font-medium text-ui-dark mb-1">
                                Address
                            </label>
                            <textarea
                                value={address}
                                onChange={(e) => setAddress(e.target.value)}
                                rows={2}
                                className="w-full border border-ui-light rounded px-3 py-2"
                            />
                        </div>

                        <div>
                            <label className="block text-sm font-medium text-ui-dark mb-1">
                                Password
                            </label>
                            <input
                                type="password"
                                required
                                value={password}
                                onChange={(e) => setPassword(e.target.value)}
                                className="w-full border border-ui-light rounded px-3 py-2"
                            />
                        </div>

                        <div>
                            <label className="block text-sm font-medium text-ui-dark mb-1">
                                Confirm password
                            </label>
                            <input
                                type="password"
                                required
                                value={confirm}
                                onChange={(e) => setConfirm(e.target.value)}
                                className="w-full border border-ui-light rounded px-3 py-2"
                            />
                        </div>

                        <button
                            type="submit"
                            disabled={submitting}
                            className="w-full bg-primary hover:bg-primary-hover text-white py-2 px-6 rounded font-semibold disabled:opacity-60"
                        >
                            {submitting
                                ? 'Creating…'
                                : teacherPlan
                                    ? 'Create account'
                                    : 'Create institution'}
                        </button>
                    </form>
                )}
            </div>
        </div>
    );
}

export default InstitutionSignup;
