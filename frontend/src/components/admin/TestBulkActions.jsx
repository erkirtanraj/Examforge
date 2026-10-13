import React, { useState } from "react";
import { toast } from "sonner";
import { Copy, Trash2, FolderInput, Eye, EyeOff, Loader2 } from "lucide-react";
import { api } from "../../lib/api";
import { FormDialog, Field, inputCls, errMsg } from "./kit";
import { Button } from "../ui/button";
import {
  AlertDialog, AlertDialogAction, AlertDialogCancel, AlertDialogContent, AlertDialogDescription, AlertDialogFooter, AlertDialogHeader, AlertDialogTitle,
} from "../ui/alert-dialog";

export function DuplicateDialog({ tests, onOpenChange, onDone }) {
  const [copies, setCopies] = useState(1);
  const [saving, setSaving] = useState(false);
  const submit = async () => {
    setSaving(true);
    try {
      const { data } = await api.post("/admin/tests/duplicate", { ids: tests.map((t) => t.id), copies: Number(copies) });
      toast.success(`Created ${data.created.length} draft${data.created.length === 1 ? "" : "s"}: ${data.created.slice(0, 3).map((c) => c.title).join(", ")}${data.created.length > 3 ? "…" : ""}`);
      onOpenChange(false);
      onDone();
    } catch (e) { toast.error(errMsg(e)); } finally { setSaving(false); }
  };
  return (
    <FormDialog open={!!tests} onOpenChange={(o) => { if (!o) setCopies(1); onOpenChange(o); }} title={tests?.length === 1 ? `Duplicate "${tests[0].title}"` : `Duplicate ${tests?.length || 0} tests`}
                onSubmit={submit} saving={saving} testid="duplicate-dialog">
      <p className="text-sm text-gray-400">Copies keep all questions, sections, marks and timers. They're numbered automatically (Mock 2 → Mock 3), saved as <b className="text-white">Draft</b>, and any live start time is cleared.</p>
      <Field label="Number of copies (1–20)">
        <input type="number" min="1" max="20" value={copies} onChange={(e) => setCopies(Math.max(1, Math.min(20, Number(e.target.value) || 1)))} className={`${inputCls} w-32`} data-testid="duplicate-copies-input" />
      </Field>
    </FormDialog>
  );
}

export function TestBulkBar({ ids, series, onClear, onDuplicate, onDone }) {
  const [target, setTarget] = useState("");
  const [busy, setBusy] = useState("");
  const [confirmDel, setConfirmDel] = useState(false);
  const run = async (action, extra = {}) => {
    setBusy(action);
    try {
      const { data } = await api.post("/admin/tests/bulk", { ids, action, ...extra });
      toast.success({ assign: "Moved", publish: "Published", unpublish: "Unpublished", delete: "Deleted" }[action] + ` ${data.affected} test${data.affected === 1 ? "" : "s"}`);
      setConfirmDel(false);
      onClear();
      onDone();
    } catch (e) { toast.error(errMsg(e)); } finally { setBusy(""); }
  };
  const btn = "border-gray-700 bg-transparent text-gray-200 hover:bg-gray-800";
  return (
    <div className="mb-3 flex flex-wrap items-center gap-2 rounded-md border border-blue-500/40 bg-blue-500/10 px-4 py-2.5 text-sm" data-testid="tests-bulk-bar">
      <span className="text-white mr-1" data-testid="tests-bulk-count">{ids.length} selected</span>
      <button onClick={onClear} className="text-gray-400 hover:text-white mr-2" data-testid="tests-clear-selection">Clear</button>
      <div className="flex items-center gap-2">
        <select value={target} onChange={(e) => setTarget(e.target.value)} className={`${inputCls} mt-0 py-1.5 w-56`} data-testid="bulk-assign-series">
          <option value="">Assign to series…</option>
          {series.map((s) => <option key={s.id} value={s.id}>{s.title}</option>)}
        </select>
        <Button size="sm" variant="outline" disabled={!target || !!busy} onClick={() => run("assign", { series_id: target })} className={btn} data-testid="bulk-assign-btn">
          {busy === "assign" ? <Loader2 className="w-4 h-4 animate-spin" /> : <><FolderInput className="w-4 h-4 mr-1" />Assign</>}
        </Button>
      </div>
      <div className="flex flex-wrap gap-2 sm:ml-auto">
        <Button size="sm" variant="outline" onClick={onDuplicate} disabled={!!busy} className={btn} data-testid="bulk-duplicate-btn"><Copy className="w-4 h-4 mr-1" />Duplicate</Button>
        <Button size="sm" variant="outline" onClick={() => run("publish")} disabled={!!busy} className={btn} data-testid="bulk-publish-btn"><Eye className="w-4 h-4 mr-1" />Publish</Button>
        <Button size="sm" variant="outline" onClick={() => run("unpublish")} disabled={!!busy} className={btn} data-testid="bulk-unpublish-btn"><EyeOff className="w-4 h-4 mr-1" />Unpublish</Button>
        <Button size="sm" onClick={() => setConfirmDel(true)} disabled={!!busy} className="bg-rose-600 hover:bg-rose-700" data-testid="bulk-delete-tests-btn"><Trash2 className="w-4 h-4 mr-1" />Delete</Button>
      </div>
      <AlertDialog open={confirmDel} onOpenChange={setConfirmDel}>
        <AlertDialogContent className="bg-[#111827] border-gray-800 text-white" data-testid="tests-delete-dialog">
          <AlertDialogHeader>
            <AlertDialogTitle>Delete {ids.length} test{ids.length === 1 ? "" : "s"}?</AlertDialogTitle>
            <AlertDialogDescription className="text-gray-400">Questions stay in the bank. Students will no longer see these tests. This cannot be undone.</AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel className="bg-transparent border-gray-700 text-gray-200 hover:bg-gray-800" data-testid="tests-delete-cancel">Cancel</AlertDialogCancel>
            <AlertDialogAction onClick={(e) => { e.preventDefault(); run("delete"); }} disabled={!!busy} className="bg-rose-600 hover:bg-rose-700" data-testid="tests-delete-confirm">
              {busy === "delete" ? <Loader2 className="w-4 h-4 animate-spin" /> : "Delete"}
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  );
}
