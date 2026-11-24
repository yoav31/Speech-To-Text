import { saveAs } from "file-saver";
import { Document, Packer, Paragraph, TextRun } from "docx";
import { jsPDF } from "jspdf";

const containsHebrew = (text = "") => {
  return /[\u0590-\u05FF]/.test(String(text));
};

const prepareText = (text = "") => {
  return String(text ?? "")
    .replace(/\r\n/g, "\n")
    .replace(/\r/g, "\n")
    .normalize("NFC")
    .trim();
};

const escapeHtml = (text = "") => {
  return String(text)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#39;");
};

const downloadTextFile = (content, filename) => {
  const safeText = prepareText(content);
  if (!safeText) {
    alert("There is no content to download.");
    return;
  }

  const blob = new Blob([safeText], { type: "text/plain;charset=utf-8" });
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = filename;
  document.body.appendChild(link);
  link.click();
  link.remove();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
};

// Hebrew: Open RTL-formatted view and print/save as PDF via browser
const generateHebrewPdf = (title, content) => {
  const safeTitle = escapeHtml(title);
  const safeContent = escapeHtml(content);

  const htmlContent = `<!DOCTYPE html>
<html dir="rtl" lang="he">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>${safeTitle}</title>
  <style>
    @page {
      size: A4;
      margin: 20mm;
    }
    body {
      font-family: "Arial", "David", "Heebo", sans-serif;
      font-size: 13pt;
      line-height: 1.7;
      color: #222;
      direction: rtl;
      text-align: right;
      background: #fff;
      margin: 0;
      padding: 16px;
    }
    .title {
      font-size: 18pt;
      font-weight: bold;
      text-align: center;
      margin-bottom: 24px;
      padding-bottom: 10px;
      border-bottom: 2px solid #333;
    }
    .content {
      white-space: pre-wrap;
      word-break: break-word;
      font-size: 12pt;
      line-height: 1.8;
    }
  </style>
</head>
<body>
  <div class="title">${safeTitle}</div>
  <div class="content">${safeContent}</div>
</body>
</html>`;

  const printWindow = window.open("", "_blank");
  if (!printWindow) {
    throw new Error("Pop-up blocked by browser");
  }

  printWindow.document.open();
  printWindow.document.write(htmlContent);
  printWindow.document.close();

  const triggerPrint = () => {
    if (printWindow.closed) return;
    printWindow.focus();
    printWindow.print();
  };

  if (printWindow.document.readyState === "complete") {
    setTimeout(triggerPrint, 300);
  } else {
    printWindow.onload = () => setTimeout(triggerPrint, 300);
  }
};

// Non-Hebrew languages: Generate PDF directly with jsPDF
const generateStandardPdf = (title, content, filename) => {
  const doc = new jsPDF({
    orientation: "portrait",
    unit: "pt",
    format: "a4",
  });

  const pageWidth = doc.internal.pageSize.getWidth();
  const pageHeight = doc.internal.pageSize.getHeight();
  const margin = 45;
  const maxWidth = pageWidth - margin * 2;
  const lineHeight = 18;

  doc.setFont("helvetica", "bold");
  doc.setFontSize(16);
  doc.text(title, pageWidth / 2, margin + 10, { align: "center" });

  doc.setFont("helvetica", "normal");
  doc.setFontSize(11);

  let cursorY = margin + 45;
  const lines = doc.splitTextToSize(content, maxWidth);

  for (let i = 0; i < lines.length; i += 1) {
    if (cursorY > pageHeight - margin) {
      doc.addPage();
      cursorY = margin + 10;
    }
    doc.text(lines[i], margin, cursorY);
    cursorY += lineHeight;
  }

  doc.save(filename);
};

const downloadPdf = ({ lang, text, hebrewTitle, standardTitle, filename }) => {
  const cleanText = prepareText(text);
  if (!cleanText) {
    alert("There is no content to generate a PDF.");
    return;
  }

  const isHebrew = lang === "he" || containsHebrew(cleanText);

  if (isHebrew) {
    try {
      generateHebrewPdf(hebrewTitle, cleanText);
    } catch (error) {
      console.error("Error generating Hebrew PDF:", error);
      alert(
        "Unable to open a window for Hebrew PDF export. Please check if a pop-up blocker is enabled."
      );
    }
    return;
  }

  try {
    generateStandardPdf(standardTitle, cleanText, filename);
  } catch (error) {
    console.error("Error generating PDF:", error);
    alert("An error occurred while generating the PDF file.");
  }
};

const downloadWordDoc = async (text, filename) => {
  const cleanText = prepareText(text);
  if (!cleanText) {
    alert("There is no content to download as a Word document.");
    return;
  }

  const isHebrew = containsHebrew(cleanText);
  const paragraphs = cleanText.split("\n").map(
    (line) =>
      new Paragraph({
        bidirectional: isHebrew,
        children: [new TextRun(line)],
      })
  );

  const doc = new Document({
    sections: [
      {
        properties: {},
        children: paragraphs,
      },
    ],
  });

  const blob = await Packer.toBlob(doc);
  saveAs(blob, filename);
};

export const handle_Download_Transcription_Txt = (transcription) => {
  downloadTextFile(transcription, "transcription.txt");
};

export const handle_Download_Transcription_Pdf = (
  language_transcription,
  transcription
) => {
  downloadPdf({
    lang: language_transcription,
    text: transcription,
    hebrewTitle: "תמליל - Transcription",
    standardTitle: "Transcription",
    filename: `transcription_${language_transcription || "en"}.pdf`,
  });
};

export const handle_Download_Transcription_Word = async (transcription) => {
  await downloadWordDoc(transcription, "transcription.docx");
};

export const handle_Download_Summary_Txt = (summarization) => {
  downloadTextFile(summarization, "summarization.txt");
};

export const handle_Download_Summary_Pdf = (
  language_summary,
  summarization
) => {
  downloadPdf({
    lang: language_summary,
    text: summarization,
    hebrewTitle: "סיכום - Summary",
    standardTitle: "Summary",
    filename: `summary_${language_summary || "en"}.pdf`,
  });
};

export const handle_Download_Summary_Word = async (summarization) => {
  await downloadWordDoc(summarization, "summarization.docx");
};