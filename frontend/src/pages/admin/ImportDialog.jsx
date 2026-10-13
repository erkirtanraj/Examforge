import React, { useRef, useState } from "react";
import { toast } from "sonner";
import { Upload, FileSpreadsheet, Download, CheckCircle2, AlertTriangle, Loader2, Undo2 } from "lucide-react";
import { Dialog, DialogContent, DialogHeader, DialogTitle } from "../../components/ui/dialog";
import { Button } from "../../components/ui/button";
import { api } from "../../lib/api";
import { Field, inputCls, CategorySelect, errMsg } from "../../components/admin/kit";

const TEMPLATE = [
  "question,type,option_a,option_b,option_c,option_d,correct,explanation,category,difficulty,positive_marks,negative_marks",
  "What is 25% of 80?,mcq,15,20,25,30,B,25% of 80 = 20,SSC CGL,easy,2,0.5",
  "Which of these are prime numbers?,multi,2,9,11,15,\"A,C\",2 and 11 have exactly two factors,SSC CGL,medium,2,0.5",
  "The Earth revolves around the Sun.,true_false,,,,,True,,SSC CGL,easy,1,0",
  "What is the value of 12 x 12?,numerical,,,,,144,,SSC CGL,easy,1,0",
].join("\n");

const downloadTemplate = () => {
  const url = URL.createObjectURL(new Blob([TEMPLATE], { type: "text/csv" }));
  Object.assign(document.createElement("a"), { href: url, download: "question-import-template.csv" }).click();
  URL.revokeObjectURL(url);
};

export default function ImportDialog({ open, onOpenChange, categories, onImported }) {
  const [file, setFile] = useState(null);
  const [opts, setOpts] = useState({ category_id: "", positive_marks: 1, negative_marks: 0 });
  const [result, setResult] = useState(null);
  const [busy, setBusy] = useState(false);
  const inputRef = useRef(null);

  const reset = () => { setFile(null); setResult(null); };
  const close = (o) => { if (!o) reset(); onOpenChange(o); };
  const send = async (f, commit) => {
    const fd = new FormData();
    fd.append("file", f);
    fd.append("commit", commit ? "true" : "false");
    Object.entries(opts).forEach(([k, v]) => fd.append(k, v));
    setBusy(true);
    try {
      const { data } = await api.post("/questions/import", fd);
      setResult(data);
      if (commit) { toast.success(`Imported ${data.inserted} questions`); onImported(); }
    } catch (e) { toast.error(errMsg(e, "Could not read the file")); if (!commit) setFile(null); }
    finally { setBusy(false); }
  };
  const pick = (f) => { if (!f) return; setFile(f); setResult(null); send(f, false); };
  const undo = async () => {
    setBusy(true);
    try { const { data } = await api.delete(`/questions/import/${result.batch_id}`); toast.success(`Removed ${data.deleted} imported questions`); onImported(); reset(); }
    catch (e) { toast.error(errMsg(e)); } finally { setBusy(false); }
  };

  return (
    <Dialog open={open} onOpenChange={close}>
      <DialogContent className="bg-[#0b1120] border-gray-800 text-white sm:max-w-2xl max-h-[90vh] overflow-y-auto" data-testid="import-dialog">
        <DialogHeader><DialogTitle className="heading-font">Bulk import questions</DialogTitle></DialogHeader>
        {result?.inserted ? (
          <div className="text-center py-6 space-y-4" data-testid="import-done">
            <CheckCircle2 className="w-12 h-12 text-emerald-400 mx-auto" />
            <div className="heading-font text-xl font-semibold">{result.inserted} questions added to the bank</div>
            {result.error_count > 0 && <div className="text-sm text-amber-300">{result.error_count} rows were skipped because of errors.</div>}
            <div className="flex justify-center gap-3">
              <Button variant="outline" onClick={undo} disabled={busy} className="border-gray-700 bg-transparent text-gray-200 hover:bg-gray-800" data-testid="import-undo-btn"><Undo2 className="w-4 h-4 mr-1" />Undo import</Button>
              <Button onClick={() => close(false)} className="bg-blue-600 hover:bg-blue-700" data-testid="import-close-btn">Done</Button>
            </div>
          </div>
        ) : (
          <div className="space-y-4">
            <div className="flex items-center justify-between text-sm text-gray-400">
              <span>Upload a <b className="text-gray-200">.csv</b> or <b className="text-gray-200">.xlsx</b> file — up to 2,000 questions.</span>
              <button onClick={downloadTemplate} className="flex items-center gap-1 text-blue-400 hover:text-blue-300" data-testid="download-template-btn"><Download className="w-4 h-4" />Template</button>
            </div>
            <div onClick={() => inputRef.current?.click()} onDragOver={(e) => e.preventDefault()}
                 onDrop={(e) => { e.preventDefault(); pick(e.dataTransfer.files?.[0]); }} data-testid="import-dropzone"
                 className="border-2 border-dashed border-gray-700 hover:border-blue-500/60 rounded-lg p-8 text-center cursor-pointer transition-colors">
              {file ? <FileSpreadsheet className="w-10 h-10 mx-auto text-cyan-300" /> : <Upload className="w-10 h-10 mx-auto text-gray-500" />}
              <div className="mt-2 text-sm text-gray-200">{file ? file.name : "Drop your file here or click to browse"}</div>
              <input ref={inputRef} type="file" accept=".csv,.xlsx,.xlsm" className="hidden" data-testid="import-file-input"
                     onChange={(e) => { pick(e.target.files?.[0]); e.target.value = ""; }} />
            </div>
            <div className="grid sm:grid-cols-3 gap-3">
              <Field label="Default category"><CategorySelect value={opts.category_id} onChange={(v) => setOpts({ ...opts, category_id: v })} categories={categories} testid="import-default-category" /></Field>
              <Field label="Default marks (+)"><input type="number" step="0.25" min="0" value={opts.positive_marks} onChange={(e) => setOpts({ ...opts, positive_marks: e.target.value })} className={inputCls} data-testid="import-default-positive" /></Field>
              <Field label="Default negative (−)"><input type="number" step="0.25" min="0" value={opts.negative_marks} onChange={(e) => setOpts({ ...opts, negative_marks: e.target.value })} className={inputCls} data-testid="import-default-negative" /></Field>
            </div>
            <p className="text-xs text-gray-500">Defaults apply to rows where the column is empty. Columns: question, type (mcq · multi · true_false · numerical), option_a…option_h, correct (letter, "A,C", option text, True/False or a number), explanation, category (name or slug), difficulty, positive_marks, negative_marks.</p>
            {busy && !result && <div className="flex items-center gap-2 text-sm text-gray-400"><Loader2 className="w-4 h-4 animate-spin" />Checking file…</div>}
            {result && <ImportPreview result={result} />}
            {result && (
              <div className="flex justify-end gap-3">
                <Button variant="outline" onClick={reset} className="border-gray-700 bg-transparent text-gray-200 hover:bg-gray-800">Choose another file</Button>
                <Button onClick={() => send(file, true)} disabled={busy || !result.valid} className="bg-blue-600 hover:bg-blue-700" data-testid="import-confirm-btn">
                  {busy ? <Loader2 className="w-4 h-4 animate-spin" /> : `Import ${result.valid} question${result.valid === 1 ? "" : "s"}`}
                </Button>
              </div>
            )}
          </div>
        )}
      </DialogContent>
    </Dialog>
  );
}

const ImportPreview = ({ result }) => (
  <div className="space-y-3" data-testid="import-preview">
    <div className="grid grid-cols-3 gap-2 text-center">
      <div className="rounded-md border border-gray-700 p-2"><div className="text-xl font-bold" data-testid="import-total">{result.total}</div><div className="text-[10px] mono-font text-gray-400">ROWS</div></div>
      <div className="rounded-md border border-emerald-500/30 bg-emerald-500/10 p-2"><div className="text-xl font-bold text-emerald-300" data-testid="import-valid">{result.valid}</div><div className="text-[10px] mono-font text-gray-400">READY</div></div>
      <div className="rounded-md border border-rose-500/30 bg-rose-500/10 p-2"><div className="text-xl font-bold text-rose-300" data-testid="import-errors">{result.error_count}</div><div className="text-[10px] mono-font text-gray-400">ERRORS</div></div>
    </div>
    {result.errors.length > 0 && (
      <div className="rounded-md border border-rose-500/30 max-h-40 overflow-y-auto divide-y divide-gray-800" data-testid="import-error-list">
        {result.errors.map((e) => (
          <div key={e.row} className="flex gap-3 px-3 py-2 text-xs"><AlertTriangle className="w-3.5 h-3.5 text-rose-300 shrink-0 mt-0.5" /><span className="mono-font text-gray-400 shrink-0">ROW {e.row}</span><span className="text-gray-200">{e.message}</span></div>
        ))}
      </div>
    )}
    {result.preview.length > 0 && (
      <div className="rounded-md border border-gray-800 divide-y divide-gray-800">
        <div className="px-3 py-2 text-[10px] mono-font text-gray-500 uppercase">Preview · first {result.preview.length}</div>
        {result.preview.map((q, i) => (
          <div key={i} className="px-3 py-2 text-xs flex gap-3"><span className="text-gray-200 flex-1 truncate">{q.text}</span><span className="mono-font text-cyan-300 shrink-0">{q.type} · {q.correct.join(",")}</span></div>
        ))}
      </div>
    )}
    {result.errors.length > 0 && <p className="text-xs text-gray-500">Rows with errors are skipped. Fix them in your sheet and import again, or continue with the valid rows.</p>}
  </div>
);
