import { useState, useEffect } from "react";
import PageHeader from "../components/PageHeader";
import {
  listContacts,
  createContact,
  updateContact,
  deleteContact,
} from "../api/contacts";

const EMPTY_FORM = { name: "", email: "", notes: "" };

export default function Contacts() {
  const [contacts, setContacts] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [form, setForm] = useState(EMPTY_FORM);
  const [editingId, setEditingId] = useState(null);
  const [saving, setSaving] = useState(false);
  const [showForm, setShowForm] = useState(false);

  useEffect(() => {
    listContacts()
      .then(setContacts)
      .catch((err) => setError(err.message))
      .finally(() => setLoading(false));
  }, []);

  function startEdit(contact) {
    setEditingId(contact.id);
    setForm({
      name: contact.name,
      email: contact.email || "",
      notes: contact.notes || "",
    });
    setShowForm(true);
  }

  function cancelForm() {
    setEditingId(null);
    setForm(EMPTY_FORM);
    setShowForm(false);
    setError(null);
  }

  async function handleSubmit(e) {
    e.preventDefault();
    setError(null);
    setSaving(true);
    try {
      if (editingId) {
        const updated = await updateContact(editingId, form);
        setContacts((prev) =>
          prev.map((c) => (c.id === editingId ? updated : c)),
        );
      } else {
        const created = await createContact(form);
        setContacts((prev) => [...prev, created]);
      }
      cancelForm();
    } catch (err) {
      setError(err.message);
    } finally {
      setSaving(false);
    }
  }

  async function handleDelete(id) {
    try {
      await deleteContact(id);
      setContacts((prev) => prev.filter((c) => c.id !== id));
    } catch (err) {
      setError(err.message);
    }
  }

  return (
    <>
      <PageHeader
        label="INTEL DATABASE / ACTIVE"
        title="OPERATOR INTEL"
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
        {error && (
          <div className="bg-error-container text-on-error-container font-body text-sm px-4 py-3">
            {error}
          </div>
        )}

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
                <div className="sm:col-span-2">
                  <label className="block font-label text-xs tracking-widest uppercase text-on-surface-variant mb-1">
                    Notes
                  </label>
                  <input
                    type="text"
                    value={form.notes}
                    onChange={(e) =>
                      setForm({ ...form, notes: e.target.value })
                    }
                    className="tactical-input"
                  />
                </div>
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

        {loading ? (
          <div className="text-center text-on-surface-variant py-16 font-label text-xs tracking-widest uppercase">
            LOADING INTEL...
          </div>
        ) : contacts.length === 0 ? (
          <div className="text-center py-16 font-label text-xs tracking-widest uppercase text-on-surface-variant">
            No contacts yet. Add one above.
          </div>
        ) : (
          <ul className="space-y-3">
            {contacts.map((c) => (
              <li
                key={c.id}
                className="bg-surface-container px-5 py-4 flex items-start justify-between gap-4"
              >
                <div className="min-w-0">
                  <p className="font-headline font-semibold text-on-surface">
                    {c.name}
                  </p>
                  {c.email && (
                    <p className="font-label text-xs tracking-widest uppercase text-on-surface-variant mt-0.5 truncate">
                      {c.email}
                    </p>
                  )}
                  {c.notes && (
                    <p className="font-body text-xs text-outline mt-1 italic">
                      {c.notes}
                    </p>
                  )}
                </div>
                <div className="flex gap-4 shrink-0">
                  <button
                    onClick={() => startEdit(c)}
                    className="font-label text-xs tracking-widest uppercase text-tertiary hover:text-tertiary-fixed transition-colors"
                  >
                    Edit
                  </button>
                  <button
                    onClick={() => handleDelete(c.id)}
                    className="font-label text-xs tracking-widest uppercase text-error hover:opacity-80 transition-opacity"
                  >
                    Delete
                  </button>
                </div>
              </li>
            ))}
          </ul>
        )}
      </main>
    </>
  );
}
