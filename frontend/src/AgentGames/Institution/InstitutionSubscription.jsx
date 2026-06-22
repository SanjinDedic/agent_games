import React, { useState, useEffect, useCallback } from 'react';
import { toast } from 'react-toastify';
import { useNavigate, useLocation } from 'react-router-dom';
import { useSelector } from 'react-redux';
import { authFetch } from '../../utils/authFetch';
import { selectToken } from '../../slices/authSlice';

// Display labels for the plan tiers (the price/amount is driven server-side).
const TIER_LABELS = {
  club: 'Club & School',
  university: 'University & Large Cohort',
};

const PAYMENT_METHOD_LABELS = {
  card: 'Card',
  invoice: 'Invoice',
  admin: 'Manually granted',
};

function formatDate(iso) {
  if (!iso) return '—';
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return '—';
  return d.toLocaleDateString(undefined, {
    year: 'numeric',
    month: 'long',
    day: 'numeric',
  });
}

function Row({ label, children }) {
  return (
    <div className="flex flex-col sm:flex-row sm:items-baseline py-3 border-b border-ui-light last:border-b-0">
      <span className="w-full sm:w-1/3 text-sm font-medium text-ui">{label}</span>
      <span className="w-full sm:w-2/3 text-ui-dark">{children}</span>
    </div>
  );
}

function InstitutionSubscription() {
  const navigate = useNavigate();
  const location = useLocation();
  const apiUrl = useSelector((state) => state.settings.agentApiUrl);
  const accessToken = useSelector(selectToken);

  const [isLoading, setIsLoading] = useState(true);
  const [data, setData] = useState(null);

  // Passed through from the invoiced signup flow so the hosted invoice link
  // isn't lost after auto-login. Only present right after signup.
  const hostedInvoiceUrl = location.state?.hostedInvoiceUrl || null;

  const fetchSubscription = useCallback(async () => {
    setIsLoading(true);
    try {
      const response = await authFetch(`${apiUrl}/institution/subscription`, {
        headers: { Authorization: `Bearer ${accessToken}` },
      });
      const json = await response.json();
      if (json.status === 'success') {
        setData(json.data);
      } else if (json.detail === 'Invalid token') {
        navigate('/Institution');
      } else {
        toast.error(json.message || 'Could not load subscription');
      }
    } catch (error) {
      console.error('Error fetching subscription:', error);
      toast.error('Could not reach the server. Please try again.');
    } finally {
      setIsLoading(false);
    }
  }, [apiUrl, accessToken, navigate]);

  useEffect(() => {
    fetchSubscription();
  }, [fetchSubscription]);

  const card = 'bg-white rounded-lg shadow-lg p-8';
  const sub = data?.subscription;
  const active = sub?.subscription_active;

  return (
    <div className="min-h-screen pt-16 bg-ui-lighter">
      <div className="w-full max-w-3xl mx-auto px-4 py-8">
        <h1 className="text-3xl font-bold text-ui-dark mb-6">Subscription</h1>

        {hostedInvoiceUrl && (
          <div className="mb-6 bg-blue-50 border border-blue-200 rounded-lg p-4">
            <p className="text-ui-dark">
              Your invoice has been issued and emailed (net 30 — no payment needed
              now).{' '}
              <a
                href={hostedInvoiceUrl}
                target="_blank"
                rel="noopener noreferrer"
                className="text-primary underline font-medium"
              >
                View or download your invoice
              </a>
            </p>
          </div>
        )}

        {isLoading ? (
          <div className={`${card} text-center text-ui`}>Loading…</div>
        ) : !data ? (
          <div className={`${card} text-center text-ui`}>
            No subscription information available.
          </div>
        ) : (
          <div className="space-y-6">
            <div className={card}>
              <h2 className="text-xl font-semibold text-ui-dark mb-4">Plan</h2>
              {sub ? (
                <div>
                  <Row label="Plan">
                    {TIER_LABELS[sub.tier] || sub.tier || 'Subscription'}
                  </Row>
                  <Row label="Status">
                    <span
                      className={`inline-block px-2 py-0.5 rounded text-sm font-medium ${
                        active
                          ? 'bg-green-100 text-green-800'
                          : 'bg-red-100 text-red-800'
                      }`}
                    >
                      {active ? 'Active' : 'Inactive'}
                    </span>
                  </Row>
                  <Row label="Expires">{formatDate(sub.subscription_expiry)}</Row>
                  <Row label="Auto-renew">{sub.auto_renew ? 'Yes' : 'No'}</Row>
                  <Row label="Billed via">
                    {PAYMENT_METHOD_LABELS[sub.payment_method] ||
                      sub.payment_method ||
                      '—'}
                  </Row>
                  <Row label="Member since">{formatDate(sub.created_date)}</Row>
                </div>
              ) : (
                <p className="text-ui">No active subscription on record.</p>
              )}
            </div>

            <div className={card}>
              <h2 className="text-xl font-semibold text-ui-dark mb-4">Contact</h2>
              <Row label="Institution">{data.institution_name}</Row>
              <Row label="Contact person">{data.contact_person || '—'}</Row>
              <Row label="Contact email">{data.contact_email || '—'}</Row>
              <Row label="Address">{data.address || '—'}</Row>
            </div>

            {sub && (sub.business_contact_name || sub.business_contact_email) && (
              <div className={card}>
                <h2 className="text-xl font-semibold text-ui-dark mb-4">
                  Billing contact
                </h2>
                <Row label="Name">{sub.business_contact_name || '—'}</Row>
                <Row label="Email">{sub.business_contact_email || '—'}</Row>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}

export default InstitutionSubscription;
