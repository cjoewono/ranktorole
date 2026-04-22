import { useState } from "react";
import { useContacts } from "../context/ContactsContext";
import PageHeader from "../components/PageHeader";
import { formatDate } from "../utils/formatDate";

const EMPTY_FORM = { name: "", email: "", company: "", role: "", notes: "" };

const AVATAR_COLORS = [
  "bg-primary/15 text-primary",
  "bg-secondary/15 text-secondary",
  "bg-tertiary/15 text-tertiary",
  "bg-error/15 text-error",
  "bg-primary/10 text-primary",
  "bg-secondary/10 text-secondary",
];

function getInitials(name) {
  const parts = name.trim().split(/\s+/);
  if (parts.length >= 2) return (parts[0][0] + parts[1][0]).toUpperCase();
  return parts[0][0].toUpperCase();
}

function hashName(name) {
  let hash = 0;
  for (let i = 0; i < name.length; i++) {
    hash = (hash * 31 + name.charCodeAt(i)) % AVATAR_COLORS.length;
  }
  return Math.abs(hash);
}

export default function Contacts() {
  const {
    contacts,
    loading,
    error,
    createContact,
    updateContact,
    deleteContact,
  } = useContacts();
  const [form, setForm] = useState(EMPTY_FORM);
  const [editingId, setEditingId] = useState(null);
  const [saving, setSaving] = useState(false);
  const [showForm, setShowForm] = useState(false);
  const [search, setSearch] = useState("");
  const [expandedId, setExpandedId] = useState(null);
  const [formError, setFormError] = useState(null);

  function startEdit(contact) {
    setEditingId(contact.id);
    setForm({
      name: contact.name || "",
      email: contact.email || "",
      company: contact.company || "",
      role: contact.role || "",
      notes: contact.notes || "",
    });
    setShowForm(true);
    setExpandedId(null);
  }

  function cancelForm() {
    setEditingId(null);
    setForm(EMPTY_FORM);
    setShowForm(false);
    setFormError(null);
  }

  async function handleSubmit(e) {
    e.preventDefault();
    setFormError(null);
    setSaving(true);
    try {
      if (editingId) {
        await updateContact(editingId, form);
      } else {
        await createContact(form);
      }
      cancelForm();
    } catch (err) {
      setFormError(err.message);
    } finally {
      setSaving(false);
    }
  }

  async function handleDelete(id) {
    await deleteContact(id);
  }

  function toggleExpand(id) {
    setExpandedId((prev) => (prev === id ? null : id));
  }

  const filtered = contacts.filter((c) => {
    if (!search.trim()) return true;
    const q = search.toLowerCase();
    return (
      c.name?.toLowerCase().includes(q) ||
      c.email?.toLowerCase().includes(q) ||
      c.company?.toLowerCase().includes(q) ||
      c.role?.toLowerCase().includes(q) ||
      c.notes?.toLowerCase().includes(q)
    );
  });

  return (
    <>
      <PageHeader
        label="INTEL / NETWORK_LOG"
        title="CONTACTS"
        action={
          !showForm && (
            <button
              onClick={() => setShowForm(true)}
              className="mission-gradient font-label text-xs tracking-widest uppercase text-on-primary px-4 py-2.5 rounded-md hover:opacity-90 transition-opacity"
            >
              + ADD CONTACT
            </button>
          )
        }
      />

      <main className="max-w-4xl mx-auto px-4 py-6 space-y-4">
        {(error || formError) && (
          <div className="bg-error-container text-on-error-container font-body text-sm px-4 py-3">
            {error || formError}
          </div>
        )}

        {/* Add/Edit form */}
        {showForm && (
          <div className="bg-surface-container-low p-6">
            <h2 className="font-headline font-semibold text-on-surface uppercase text-sm tracking-wide mb-5">
              {editingId ? "EDIT CONTACT" : "NEW CONTACT"}
            </h2>
            <form onSubmit={handleSubmit} className="space-y-5">
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-5">
                <div>
                  <label className="block font-label text-xs tracking-widest uppercase text-on-surface-variant mb-1">
                    Name <span className="text-error">*</span>
                  </label>
                  <input
                    type="text"
                    required
                    value={form.name}
                    onChange={(e) => setForm({ ...form, name: e.target.value })}
                    className="tactical-input"
                  />
                </div>
                <div>
                  <label className="block font-label text-xs tracking-widest uppercase text-on-surface-variant mb-1">
                    Email
                  </label>
                  <input
                    type="email"
                    value={form.email}
                    onChange={(e) =>
                      setForm({ ...form, email: e.target.value })
                    }
                    className="tactical-input"
                  />
                </div>
                <div>
                  <label className="block font-label text-xs tracking-widest uppercase text-on-surface-variant mb-1">
                    Company
                  </label>
                  <input
                    type="text"
                    value={form.company}
                    onChange={(e) =>
                      setForm({ ...form, company: e.target.value })
                    }
                    className="tactical-input"
                  />
                </div>
                <div>
                  <label className="block font-label text-xs tracking-widest uppercase text-on-surface-variant mb-1">
                    Role
                  </label>
                  <input
                    type="text"
                    value={form.role}
                    onChange={(e) => setForm({ ...form, role: e.target.value })}
                    className="tactical-input"
                    placeholder="Recruiter, Engineering Manager…"
                  />
                </div>
              </div>
              <div>
                <label className="block font-label text-xs tracking-widest uppercase text-on-surface-variant mb-1">
                  Notes
                </label>
                <textarea
                  rows={3}
                  value={form.notes}
                  onChange={(e) => setForm({ ...form, notes: e.target.value })}
                  className="tactical-input resize-none"
                />
              </div>
              <div className="flex gap-4 pt-2">
                <button
                  type="submit"
                  disabled={saving}
                  className="mission-gradient font-label text-xs tracking-widest uppercase text-on-primary px-6 py-2.5 rounded-md disabled:opacity-50 transition-opacity"
                >
                  {saving
                    ? "SAVING..."
                    : editingId
                      ? "SAVE CHANGES"
                      : "ADD CONTACT"}
                </button>
                <button
                  type="button"
                  onClick={cancelForm}
                  className="font-label text-xs tracking-widest uppercase text-on-surface-variant hover:text-on-surface transition-colors px-4 py-2.5"
                >
                  CANCEL
                </button>
              </div>
            </form>
          </div>
        )}

        {/* Stats bar + search */}
        {!loading && (
          <div className="flex items-center gap-4 flex-wrap">
            <span className="font-label text-xs tracking-widest uppercase text-on-surface-variant bg-surface-container px-3 py-1.5">
              {contacts.length} CONTACT{contacts.length !== 1 ? "S" : ""}
            </span>
            {contacts.length > 0 && (
              <div className="relative flex-1 min-w-[180px] max-w-xs">
                <input
                  type="text"
                  value={search}
                  onChange={(e) => setSearch(e.target.value)}
                  placeholder="Search contacts…"
                  className="tactical-input pr-8 w-full"
                />
                {search && (
                  <button
                    type="button"
                    onClick={() => setSearch("")}
                    className="absolute right-2 top-1/2 -translate-y-1/2 text-on-surface-variant hover:text-on-surface transition-colors font-label text-sm"
                    aria-label="Clear search"
                  >
                    ×
                  </button>
                )}
              </div>
            )}
          </div>
        )}

        {/* Loading */}
        {loading ? (
          <div className="text-center text-on-surface-variant py-16 font-label text-xs tracking-widest uppercase">
            LOADING INTEL...
          </div>
        ) : contacts.length === 0 ? (
          /* Empty state */
          <div className="flex flex-col items-center justify-center py-20 text-center space-y-4">
            <span className="text-3xl text-on-surface-variant">◈</span>
            <p className="font-label text-xs tracking-widest uppercase text-on-surface">
              NO CONTACTS YET
            </p>
            <p className="font-body text-sm text-on-surface-variant max-w-sm">
              Start building your network — add recruiters, mentors, and
              connections you meet during your career transition.
            </p>
            <button
              onClick={() => setShowForm(true)}
              className="mission-gradient font-label text-xs tracking-widest uppercase text-on-primary px-6 py-2.5 rounded-md hover:opacity-90 transition-opacity mt-2"
            >
              + ADD YOUR FIRST CONTACT
            </button>
          </div>
        ) : filtered.length === 0 ? (
          /* No search results */
          <div className="text-center py-12 font-label text-xs tracking-widest uppercase text-on-surface-variant">
            No contacts match your search.
          </div>
        ) : (
          /* Contact grid */
          <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
            {filtered.map((c) => {
              const colorClass = AVATAR_COLORS[hashName(c.name)];
              const initials = getInitials(c.name);
              const isExpanded = expandedId === c.id;
              const roleCompany =
                c.role && c.company
                  ? `${c.role} at ${c.company}`
                  : c.role || c.company || null;

              return (
                <div
                  key={c.id}
                  className="bg-surface-container p-5 flex flex-col gap-3 cursor-pointer select-none"
                  onClick={() => toggleExpand(c.id)}
                >
                  {/* Top row: avatar + info */}
                  <div className="flex items-start gap-4">
                    <div
                      className={`w-10 h-10 rounded-full flex items-center justify-center shrink-0 font-headline font-semibold text-sm ${colorClass}`}
                    >
                      {initials}
                    </div>
                    <div className="min-w-0 flex-1">
                      <p className="font-headline font-semibold text-on-surface">
                        {c.name}
                      </p>
                      {roleCompany && (
                        <p className="font-body text-sm text-on-surface-variant mt-0.5">
                          {roleCompany}
                        </p>
                      )}
                      {c.email && (
                        <a
                          href={`mailto:${c.email}`}
                          onClick={(e) => e.stopPropagation()}
                          className="font-label text-xs tracking-widest text-primary hover:opacity-80 transition-opacity mt-0.5 block truncate"
                        >
                          {c.email}
                        </a>
                      )}
                    </div>
                  </div>

                  {/* Notes */}
                  {c.notes && (
                    <p
                      className={`font-body text-xs text-outline italic ${isExpanded ? "" : "line-clamp-2"}`}
                    >
                      {c.notes}
                    </p>
                  )}

                  {/* Footer: date + actions */}
                  <div className="flex items-center justify-between mt-auto pt-1">
                    <span className="font-label text-xs tracking-widest uppercase text-outline">
                      {formatDate(c.created_at, { uppercase: true })}
                    </span>
                    <div
                      className="flex gap-4"
                      onClick={(e) => e.stopPropagation()}
                    >
                      <button
                        onClick={() => startEdit(c)}
                        className="font-label text-xs tracking-widest uppercase text-tertiary hover:opacity-80 transition-opacity"
                      >
                        EDIT
                      </button>
                      <button
                        onClick={() => handleDelete(c.id)}
                        className="font-label text-xs tracking-widest uppercase text-error hover:opacity-80 transition-opacity"
                      >
                        DELETE
                      </button>
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </main>
    </>
  );
}
