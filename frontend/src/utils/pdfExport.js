import jsPDF from "jspdf";

export function exportPDF({ civilian_title, summary, roles }) {
  const doc = new jsPDF({ unit: "mm", format: "a4" });
  const marginL = 20,
    marginR = 20,
    marginT = 20;
  const pageW = 210,
    contentW = pageW - marginL - marginR;
  let y = marginT;

  const checkPage = () => {
    if (y > 270) {
      doc.addPage();
      y = marginT;
    }
  };

  doc.setFont("helvetica", "bold");
  doc.setFontSize(18);
  doc.text(civilian_title || "Resume", marginL, y);
  y += 8;
  doc.setDrawColor(200, 200, 200);
  doc.line(marginL, y, pageW - marginR, y);

  y += 10;
  checkPage();
  doc.setFont("helvetica", "bold");
  doc.setFontSize(10);
  doc.text("Summary", marginL, y);

  y += 5;
  doc.setFont("helvetica", "normal");
  doc.setFontSize(10);
  const summaryLines = doc.splitTextToSize(summary || "", contentW);
  summaryLines.forEach((line) => {
    checkPage();
    doc.text(line, marginL, y);
    y += 5;
  });
  y += 6;

  (roles || []).forEach((role) => {
    y += 10;
    checkPage();
    doc.setFont("helvetica", "bold");
    doc.setFontSize(11);
    doc.text(role.title || "", marginL, y);

    y += 6;
    checkPage();
    doc.setFont("helvetica", "normal");
    doc.setFontSize(9);
    doc.setTextColor(100, 100, 100);
    const orgDates = [role.org, role.dates].filter(Boolean).join(" · ");
    doc.text(orgDates, marginL, y);
    doc.setTextColor(0, 0, 0);

    doc.setFontSize(10);
    (role.bullets || []).forEach((bullet) => {
      const lines = doc.splitTextToSize(`• ${bullet}`, contentW - 6);
      lines.forEach((line) => {
        y += 5;
        checkPage();
        doc.text(line, marginL + 6, y);
      });
      y += 3;
    });
    y += 6;
  });

  const filename =
    (civilian_title || "resume").replace(/\s+/g, "_") + "_resume.pdf";
  doc.save(filename);
}
