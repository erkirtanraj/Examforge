import { jsPDF } from "jspdf";

const hexRgb = (hex) => [1, 3, 5].map((i) => parseInt(hex.slice(i, i + 2), 16));

// Landscape A4 certificate drawn as vectors (no external fonts or images).
export function downloadCertificate(cert, { brand = "ExamForge", primary = "#2563eb", accent = "#06b6d4", verifyUrl }) {
  const doc = new jsPDF({ orientation: "landscape", unit: "mm", format: "a4" });
  const W = 297, H = 210, P = hexRgb(primary), A = hexRgb(accent);
  doc.setFillColor(9, 13, 22); doc.rect(0, 0, W, H, "F");
  doc.setDrawColor(...P); doc.setLineWidth(1.2); doc.rect(10, 10, W - 20, H - 20);
  doc.setDrawColor(...A); doc.setLineWidth(0.4); doc.rect(14, 14, W - 28, H - 28);
  doc.setFillColor(...P); doc.rect(14, 14, 6, H - 28, "F");

  doc.setTextColor(...A); doc.setFont("helvetica", "bold"); doc.setFontSize(12);
  doc.text(brand.toUpperCase(), W / 2, 36, { align: "center", charSpace: 2 });
  doc.setTextColor(255, 255, 255); doc.setFontSize(34);
  doc.text("Certificate of Completion", W / 2, 58, { align: "center" });
  doc.setFont("helvetica", "normal"); doc.setFontSize(13); doc.setTextColor(170, 178, 192);
  doc.text("This certifies that", W / 2, 78, { align: "center" });
  doc.setFont("helvetica", "bold"); doc.setFontSize(30); doc.setTextColor(255, 255, 255);
  doc.text(cert.name, W / 2, 96, { align: "center", maxWidth: W - 60 });
  doc.setDrawColor(...P); doc.setLineWidth(0.6); doc.line(W / 2 - 60, 101, W / 2 + 60, 101);
  doc.setFont("helvetica", "normal"); doc.setFontSize(13); doc.setTextColor(170, 178, 192);
  doc.text("has successfully completed all lessons of the course", W / 2, 115, { align: "center" });
  doc.setFont("helvetica", "bold"); doc.setFontSize(20); doc.setTextColor(...A);
  doc.text(cert.course_title, W / 2, 130, { align: "center", maxWidth: W - 60 });

  const issued = new Date(cert.issued_at).toLocaleDateString("en-IN", { day: "numeric", month: "long", year: "numeric" });
  doc.setFont("helvetica", "normal"); doc.setFontSize(10); doc.setTextColor(150, 158, 172);
  doc.text("DATE OF ISSUE", 50, 165); doc.text("CERTIFICATE ID", W - 50, 165, { align: "right" });
  doc.setFont("helvetica", "bold"); doc.setFontSize(13); doc.setTextColor(255, 255, 255);
  doc.text(issued, 50, 173); doc.text(cert.id, W - 50, 173, { align: "right" });
  doc.setFont("helvetica", "normal"); doc.setFontSize(9); doc.setTextColor(120, 128, 142);
  doc.text(`Verify at ${verifyUrl}`, W / 2, 188, { align: "center" });
  doc.save(`${brand}-certificate-${cert.id}.pdf`);
}
