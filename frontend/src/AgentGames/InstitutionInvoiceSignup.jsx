import React, { useState } from 'react';
import { useSearchParams, useNavigate, Link } from 'react-router-dom';
import { useDispatch } from 'react-redux';
import { toast } from 'react-toastify';
import { setToken } from '../slices/authSlice';

const apiUrl = import.meta.env.VITE_AGENT_API_URL;

// Display-only metadata for the annual (invoiced) plan, keyed by tier. The
// actual amount charged is driven server-side by the Stripe Price.
const TIERS = {
    club: { label: 'Club & School', yearPrice: 299 },
    university: { label: 'University & Large Cohort', yearPrice: 599 },
};

function InstitutionInvoiceSignup() {
    const [searchParams] = useSearchParams();
    const navigate = useNavigate();
    const dispatch = useDispatch();
    const tier = searchParams.get('tier');
    const tierInfo = TIERS[tier];

    const [form, setForm] = useState({
        institution_name: '',
        institution_address: '',
        business_contact_name: '',
        business_contact_email: '',
        teaching_contact_name: '',
        teaching_contact_email: '',
        password: '',
        confirm: '',
    });
    const [submitting, setSubmitting] = useState(false);

    const update = (field) => (e) =>
        setForm((s) => ({ ...s, [field]: e.target.value }));

    const card = 'bg-white rounded-lg shadow-lg p-8 border border-ui-light';

    const handleSubmit = async (e) => {
        e.preventDefault();
        if (form.password !== form.confirm) {
            toast.error('Passwords do not match');
            return;
        }
        if (form.password.length < 8) {
            toast.error('Password must be at least 8 characters');
            return;
        }
        setSubmitting(true);
        try {
            const res = await fetch(`${apiUrl}/payments/invoice-signup`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    tier,
                    institution_name: form.institution_name,
                    institution_address: form.institution_address,
                    business_contact_name: form.business_contact_name,
                    business_contact_email: form.business_contact_email,
                    teaching_contact_name: form.teaching_contact_name,
                    teaching_contact_email: form.teaching_contact_email,
                    password: form.password,
                }),
            });
            const json = await res.json();
            if (!res.ok) {
                toast.error(json?.detail || 'Signup failed. Please try again.');
                return;
            }
            // Access is already granted and Stripe has emailed the invoice
            // (net 30 — no payment needed now). Auto-login and land on the
            // home page, passing the hosted invoice link through so it's
            // surfaced there rather than lost.
            toast.success('Institution created — your invoice has been issued.');
            const token = json?.access_token;
            const hostedInvoiceUrl = json?.hosted_invoice_url || null;
            if (token) {
                dispatch(setToken(token));
                navigate('/InstitutionHome', {
                    state: { hostedInvoiceUrl },
                });
            } else {
                navigate('/Institution');
            }
        } catch (err) {
            toast.error('Could not reach the server. Please try again.');
        } finally {
            setSubmitting(false);
        }
    };

    const field = (label, name, type = 'text', placeholder = '') => (
        <div>
            <label className="block text-sm font-medium text-ui-dark mb-1">
                {label}
            </label>
            <input
                type={type}
                required
                value={form[name]}
                onChange={update(name)}
                placeholder={placeholder}
                className="w-full border border-ui-light rounded px-3 py-2"
            />
        </div>
    );

    return (
        <div className="min-h-screen pt-16 bg-ui-lighter">
            <div className="w-full max-w-xl mx-auto px-4 py-12">
                <h1 className="text-3xl font-bold text-ui-dark mb-2 text-center">
                    Sign up &amp; get invoiced
                </h1>
                <p className="text-center text-ui mb-6">
                    Annual subscription billed by invoice (net 30). Access is granted
                    as soon as your invoice is issued — you do not need to pay first.
                </p>

                {!tierInfo ? (
                    <div className={`${card} text-center`}>
                        <p className="text-red-600 mb-4">
                            Missing or unknown plan. Please start from the pricing page.
                        </p>
                        <Link to="/Institutions" className="text-primary underline">
                            Back to pricing
                        </Link>
                    </div>
                ) : (
                    <form onSubmit={handleSubmit} className={`${card} space-y-4`}>
                        <p className="text-sm text-ui">
                            Plan:{' '}
                            <span className="font-semibold text-ui-dark">
                                {tierInfo.label}
                            </span>{' '}
                            — ${tierInfo.yearPrice} AUD / year, invoiced annually
                        </p>

                        {field('Institution name', 'institution_name')}
                        {field('Institution address', 'institution_address')}

                        <div className="border-t border-ui-light pt-4">
                            <p className="text-sm font-semibold text-ui-dark mb-3">
                                Business contact (responsible for paying the invoice)
                            </p>
                            <div className="space-y-4">
                                {field('Business contact name', 'business_contact_name')}
                                {field(
                                    'Business contact email',
                                    'business_contact_email',
                                    'email'
                                )}
                            </div>
                        </div>

                        <div className="border-t border-ui-light pt-4">
                            <p className="text-sm font-semibold text-ui-dark mb-3">
                                Teaching contact (manages teams &amp; leagues, logs in)
                            </p>
                            <div className="space-y-4">
                                {field('Teaching contact name', 'teaching_contact_name')}
                                {field(
                                    'Teaching contact email',
                                    'teaching_contact_email',
                                    'email'
                                )}
                            </div>
                        </div>

                        <div className="border-t border-ui-light pt-4">
                            <p className="text-sm font-semibold text-ui-dark mb-3">
                                Login password (for the teaching contact)
                            </p>
                            <div className="space-y-4">
                                {field('Password', 'password', 'password')}
                                {field('Confirm password', 'confirm', 'password')}
                            </div>
                        </div>

                        <button
                            type="submit"
                            disabled={submitting}
                            className="w-full bg-primary hover:bg-primary-hover text-white py-2 px-6 rounded font-semibold disabled:opacity-60"
                        >
                            {submitting
                                ? 'Creating…'
                                : 'Create institution & issue invoice'}
                        </button>
                        <p className="text-xs text-ui text-center">
                            You will be taken to a secure Stripe invoice page.
                        </p>
                    </form>
                )}
            </div>
        </div>
    );
}

export default InstitutionInvoiceSignup;
