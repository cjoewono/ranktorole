/**
 * TacticalLabel — canonical form label primitive.
 * Renders a label styled with the .label-tactical utility (font-label, text-xs,
 * tracking-widest, uppercase) over a muted surface-variant color.
 * Pass htmlFor to associate the label with its input for accessibility.
 * Use as a wrapper: <TacticalLabel htmlFor="field-id">Field Name</TacticalLabel>
 */
function TacticalLabel({ children, htmlFor }) {
  return (
    <label
      htmlFor={htmlFor}
      className="block font-label text-xs tracking-widest uppercase text-on-surface-variant mb-1"
    >
      {children}
    </label>
  );
}

export { TacticalLabel };
export default TacticalLabel;
