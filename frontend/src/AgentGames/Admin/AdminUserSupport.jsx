import React, { useCallback, useEffect, useMemo, useState } from 'react';
import { toast } from 'react-toastify';
import { useNavigate } from 'react-router-dom';
import { useDispatch, useSelector } from 'react-redux';
import moment from 'moment-timezone';
import { checkTokenExpiry } from '../../slices/authSlice';
import { authFetch } from '../../utils/authFetch';

const SUBMITTER_TABS = [
  { key: 'team', label: 'Users' },
  { key: 'institution', label: 'Institutions' },
];

const STATUS_OPTIONS = [
  { value: 'all', label: 'All statuses' },
  { value: 'open', label: 'Open' },
  { value: 'in_progress', label: 'In progress' },
  { value: 'resolved', label: 'Resolved' },
];

const CATEGORY_STYLES = {
  bug: 'bg-danger-light text-danger',
  support: 'bg-league-text text-league-blue',
  feedback: 'bg-success-light text-success',
};

function AdminUserSupport() {
  const navigate = useNavigate();
  const dispatch = useDispatch();
  const apiUrl = useSelector((state) => state.settings.agentApiUrl);
  const accessToken = useSelector((state) => state.auth.token);
  const currentUser = useSelector((state) => state.auth.currentUser);
  const isAuthenticated = useSelector((state) => state.auth.isAuthenticated);

  const [submitterTab, setSubmitterTab] = useState('team');
  const [statusFilter, setStatusFilter] = useState('all');
  const [tickets, setTickets] = useState([]);
  const [isLoading, setIsLoading] = useState(true);
  const [noteDrafts, setNoteDrafts] = useState({});
  const [savingId, setSavingId] = useState(null);
  const [deletingId, setDeletingId] = useState(null);
  const [lightboxUrl, setLightboxUrl] = useState(null);

  useEffect(() => {
    const tokenExpired = dispatch(checkTokenExpiry());
    if (!isAuthenticated || currentUser.role !== 'admin' || tokenExpired) {
      navigate('/Admin');
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const fetchTickets = useCallback(() => {
    setIsLoading(true);
    const params = new URLSearchParams({ submitter_type: submitterTab });
    if (statusFilter !== 'all') params.append('status', statusFilter);
    authFetch(`${apiUrl}/admin/support-tickets?${params.toString()}`, {
      headers: { Authorization: `Bearer ${accessToken}` },
    })
      .then((res) => res.json())
      .then((data) => {
        if (data.status === 'success') {
          const list = data.data?.tickets || [];
          setTickets(list);
          setNoteDrafts(
            list.reduce((acc, t) => {
              acc[t.id] = t.admin_note || '';
              return acc;
            }, {})
          );
        } else {
          toast.error(data.message || 'Failed to load tickets');
        }
      })
      .catch((err) => {
        console.error('Error fetching support tickets:', err);
        toast.error('Error connecting to server');
      })
      .finally(() => setIsLoading(false));
  }, [apiUrl, accessToken, submitterTab, statusFilter]);

  useEffect(() => {
    fetchTickets();
  }, [fetchTickets]);

  const deleteTicket = (ticket) => {
    const confirmMsg =
      ticket.attachments?.length > 0
        ? `Delete this ticket and its ${ticket.attachments.length} attachment(s)? This cannot be undone.`
        : 'Delete this ticket? This cannot be undone.';
    if (!window.confirm(confirmMsg)) return;

    setDeletingId(ticket.id);
    authFetch(`${apiUrl}/admin/support-ticket/${ticket.id}`, {
      method: 'DELETE',
      headers: { Authorization: `Bearer ${accessToken}` },
    })
      .then((res) => res.json())
      .then((data) => {
        if (data.status === 'success') {
          setTickets((prev) => prev.filter((t) => t.id !== ticket.id));
          setNoteDrafts((prev) => {
            const next = { ...prev };
            delete next[ticket.id];
            return next;
          });
          toast.success('Ticket deleted');
        } else {
          toast.error(data.message || 'Failed to delete ticket');
        }
      })
      .catch((err) => {
        console.error('Error deleting ticket:', err);
        toast.error('Error connecting to server');
      })
      .finally(() => setDeletingId(null));
  };

  const updateTicket = (ticketId, payload) => {
    setSavingId(ticketId);
    authFetch(`${apiUrl}/admin/support-ticket-update`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        Authorization: `Bearer ${accessToken}`,
      },
      body: JSON.stringify({ ticket_id: ticketId, ...payload }),
    })
      .then((res) => res.json())
      .then((data) => {
        if (data.status === 'success' && data.data?.ticket) {
          const updated = data.data.ticket;
          setTickets((prev) => prev.map((t) => (t.id === updated.id ? updated : t)));
          setNoteDrafts((prev) => ({ ...prev, [updated.id]: updated.admin_note || '' }));
          toast.success('Ticket updated');
        } else {
          toast.error(data.message || 'Failed to update ticket');
        }
      })
      .catch((err) => {
        console.error('Error updating ticket:', err);
        toast.error('Error connecting to server');
      })
      .finally(() => setSavingId(null));
  };

  const statusBadge = useMemo(
    () => ({
      open: 'bg-notice-yellowBg text-notice-yellow',
      in_progress: 'bg-league-text text-league-blue',
      resolved: 'bg-success-light text-success',
    }),
    []
  );

  return (
    <div className="min-h-screen bg-ui-lighter pt-20 px-6 pb-8">
      <div className="max-w-7xl mx-auto">
        <div className="bg-white rounded-lg shadow-lg p-6">
          <div className="flex items-center justify-between mb-6 flex-wrap gap-3">
            <h1 className="text-2xl font-bold text-ui-dark">User Support</h1>
            <button
              onClick={fetchTickets}
              className="px-3 py-2 text-sm border border-ui-light rounded-lg hover:bg-ui-lighter"
            >
              Refresh
            </button>
          </div>

          <div className="flex items-center justify-between mb-4 flex-wrap gap-3">
            <div className="flex border border-ui-light rounded-lg overflow-hidden">
              {SUBMITTER_TABS.map((tab) => (
                <button
                  key={tab.key}
                  onClick={() => setSubmitterTab(tab.key)}
                  className={`px-4 py-2 text-sm transition-colors ${
                    submitterTab === tab.key
                      ? 'bg-primary text-white'
                      : 'bg-white text-ui-dark hover:bg-ui-lighter'
                  }`}
                >
                  {tab.label}
                </button>
              ))}
            </div>

            <select
              value={statusFilter}
              onChange={(e) => setStatusFilter(e.target.value)}
              className="p-2 border border-ui-light rounded-lg bg-white text-ui-dark"
            >
              {STATUS_OPTIONS.map((opt) => (
                <option key={opt.value} value={opt.value}>
                  {opt.label}
                </option>
              ))}
            </select>
          </div>

          {isLoading ? (
            <div className="flex justify-center items-center h-32">
              <div className="text-lg text-ui-dark">Loading tickets…</div>
            </div>
          ) : tickets.length === 0 ? (
            <div className="text-center py-8">
              <p className="text-lg text-ui">
                No {submitterTab === 'team' ? 'user' : 'institution'} tickets found.
              </p>
            </div>
          ) : (
            <ul className="space-y-4">
              {tickets.map((ticket) => (
                <li
                  key={ticket.id}
                  className="border border-ui-light rounded-lg p-4 bg-white"
                >
                  <div className="flex items-start justify-between flex-wrap gap-2">
                    <div>
                      <div className="flex items-center gap-2 mb-1">
                        <span
                          className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium ${
                            CATEGORY_STYLES[ticket.category] || 'bg-ui-light text-ui-dark'
                          }`}
                        >
                          {ticket.category}
                        </span>
                        <span
                          className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium ${
                            statusBadge[ticket.status] || 'bg-ui-light text-ui-dark'
                          }`}
                        >
                          {ticket.status.replace('_', ' ')}
                        </span>
                      </div>
                      <h3 className="text-lg font-semibold text-ui-dark">
                        {ticket.subject}
                      </h3>
                      <p className="text-sm text-ui mt-1">
                        From{' '}
                        <span className="font-medium text-ui-dark">
                          {ticket.submitter?.name || 'Unknown'}
                        </span>
                        {ticket.submitter?.institution_name && (
                          <> · {ticket.submitter.institution_name}</>
                        )}
                        {ticket.submitter?.contact_email && (
                          <> · {ticket.submitter.contact_email}</>
                        )}
                        {' · '}
                        {moment(ticket.created_at).format('MMM DD, YYYY HH:mm')}
                      </p>
                    </div>

                    <div className="flex items-center gap-2">
                      <select
                        value={ticket.status}
                        onChange={(e) =>
                          updateTicket(ticket.id, { status: e.target.value })
                        }
                        disabled={savingId === ticket.id || deletingId === ticket.id}
                        className="p-2 border border-ui-light rounded-lg bg-white text-ui-dark disabled:opacity-50"
                      >
                        <option value="open">Open</option>
                        <option value="in_progress">In progress</option>
                        <option value="resolved">Resolved</option>
                      </select>
                      <button
                        onClick={() => deleteTicket(ticket)}
                        disabled={deletingId === ticket.id || savingId === ticket.id}
                        className="p-2 text-danger hover:text-danger-hover disabled:opacity-50"
                        title="Delete ticket"
                        aria-label="Delete ticket"
                      >
                        <svg
                          xmlns="http://www.w3.org/2000/svg"
                          className="h-5 w-5"
                          viewBox="0 0 20 20"
                          fill="currentColor"
                        >
                          <path
                            fillRule="evenodd"
                            d="M9 2a1 1 0 00-.894.553L7.382 4H4a1 1 0 000 2v10a2 2 0 002 2h8a2 2 0 002-2V6a1 1 0 100-2h-3.382l-.724-1.447A1 1 0 0011 2H9zM7 8a1 1 0 012 0v6a1 1 0 11-2 0V8zm5-1a1 1 0 00-1 1v6a1 1 0 102 0V8a1 1 0 00-1-1z"
                            clipRule="evenodd"
                          />
                        </svg>
                      </button>
                    </div>
                  </div>

                  <p className="mt-3 text-ui-dark whitespace-pre-wrap">
                    {ticket.description}
                  </p>

                  {ticket.attachments?.length > 0 && (
                    <div className="mt-3 flex flex-wrap gap-2">
                      {ticket.attachments.map((att) => (
                        <button
                          key={att.id}
                          type="button"
                          onClick={() => setLightboxUrl(att.url)}
                          className="border border-ui-light rounded overflow-hidden focus:outline-none focus:ring-2 focus:ring-primary-light"
                          title={att.original_filename}
                        >
                          <img
                            src={att.url}
                            alt={att.original_filename}
                            className="w-24 h-24 object-cover"
                          />
                        </button>
                      ))}
                    </div>
                  )}

                  <div className="mt-4">
                    <label className="block text-xs text-ui mb-1">
                      Internal admin note
                    </label>
                    <textarea
                      value={noteDrafts[ticket.id] ?? ''}
                      onChange={(e) =>
                        setNoteDrafts((prev) => ({ ...prev, [ticket.id]: e.target.value }))
                      }
                      rows={2}
                      className="w-full p-2 border border-ui-light rounded-lg"
                      placeholder="Only visible to admins"
                      disabled={savingId === ticket.id}
                    />
                    <div className="flex justify-end mt-2">
                      <button
                        onClick={() =>
                          updateTicket(ticket.id, {
                            admin_note: noteDrafts[ticket.id] || '',
                          })
                        }
                        disabled={
                          savingId === ticket.id ||
                          (noteDrafts[ticket.id] || '') === (ticket.admin_note || '')
                        }
                        className="px-3 py-1 text-sm bg-primary hover:bg-primary-hover text-white rounded-lg disabled:opacity-50"
                      >
                        {savingId === ticket.id ? 'Saving…' : 'Save note'}
                      </button>
                    </div>
                  </div>
                </li>
              ))}
            </ul>
          )}
        </div>
      </div>

      {lightboxUrl && (
        <div
          className="fixed inset-0 z-[70] bg-black/80 flex items-center justify-center px-4"
          onClick={() => setLightboxUrl(null)}
        >
          <img
            src={lightboxUrl}
            alt="Attachment"
            className="max-h-[90vh] max-w-full rounded-lg shadow-xl"
          />
        </div>
      )}
    </div>
  );
}

export default AdminUserSupport;
