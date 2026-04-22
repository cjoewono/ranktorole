import { createContext, useContext, useState, useEffect } from "react";
import {
  listContacts,
  createContact as apiCreateContact,
  updateContact as apiUpdateContact,
  deleteContact as apiDeleteContact,
} from "../api/contacts";

const ContactsContext = createContext(null);

export function ContactsProvider({ children }) {
  const [contacts, setContacts] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  async function refreshContacts() {
    setLoading(true);
    try {
      const data = await listContacts();
      setContacts(data);
      setError(null);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    refreshContacts();
  }, []);

  async function createContact(data) {
    const created = await apiCreateContact(data);
    setContacts((prev) => [...prev, created]);
    return created;
  }

  async function updateContact(id, data) {
    const updated = await apiUpdateContact(id, data);
    setContacts((prev) => prev.map((c) => (c.id === id ? updated : c)));
    return updated;
  }

  async function deleteContact(id) {
    setContacts((prev) => prev.filter((c) => c.id !== id));
    try {
      await apiDeleteContact(id);
    } catch (err) {
      setError(err.message);
      listContacts()
        .then(setContacts)
        .catch(() => {});
    }
  }

  return (
    <ContactsContext.Provider
      value={{
        contacts,
        loading,
        error,
        refreshContacts,
        createContact,
        updateContact,
        deleteContact,
      }}
    >
      {children}
    </ContactsContext.Provider>
  );
}

// Exposes: { contacts, loading, error, refreshContacts, createContact, updateContact, deleteContact }
export function useContacts() {
  return useContext(ContactsContext);
}
