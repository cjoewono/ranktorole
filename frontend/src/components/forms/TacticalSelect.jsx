/**
 * TacticalSelect — canonical styled select primitive.
 * Applies tactical-input styling plus appearance-none for custom arrow styling.
 * Props: value, onChange, required, id, name, children (option elements).
 */
function TacticalSelect({ value, onChange, required, id, name, children }) {
  return (
    <select
      id={id}
      name={name}
      required={required}
      value={value}
      onChange={onChange}
      className="tactical-input appearance-none cursor-pointer"
    >
      {children}
    </select>
  );
}

export { TacticalSelect };
export default TacticalSelect;
