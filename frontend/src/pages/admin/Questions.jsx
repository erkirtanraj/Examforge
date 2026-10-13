import React, { useCallback, useEffect, useMemo, useState } from "react";
import { toast } from "sonner";
import { Upload, Trash2, ChevronLeft, ChevronRight, Loader2 } from "lucide-react";
import { api } from "../../lib/api";
import { PageHeader, DataTable, Pill, RowActions, NewButton, inputCls, CategorySelect, SubjectSelect, useCategories, useSubjects, errMsg } from "../../components/admin/kit";
import QuestionForm from "./QuestionForm";
import ImportDialog from "./ImportDialog";
import { Button } from "../../components/ui/button";
import {
  AlertDialog, AlertDialogAction, AlertDialogCancel, AlertDialogContent, AlertDialogDescription, AlertDialogFooter, AlertDialogHeader, AlertDialogTitle,
} from "../../components/ui/alert-dialog";

const TYPE_LABEL = { mcq_single: "MCQ", mcq_multi: "MULTI", true_false: "T/F", numerical: "NUM" };
const DIFF_TONE = { easy: "emerald", medium: "amber", hard: "rose" };
const SIZES = [10, 50, 100, 500, 1000, 5000];
const EMPTY = { search: "", category_id: "", subject_id: "", difficulty: "", type: "" };

function useDebounced(v, ms = 350) {
  const [d, setD] = useState(v);
  useEffect(() => { const t = setTimeout(() => setD(v), ms); return () => clearTimeout(t); }, [v, ms]);
  return d;
}

export default function Questions() {
  const cats = useCategories();
  const [subs] = useSubjects();
  const [filters, setFilters] = useState(EMPTY);
  const search = useDebounced(filters.search);
  const [page, setPage] = useState(1);
  const [size, setSize] = useState(50);
  const [data, setData] = useState({ items: [], total: 0, pages: 1, grand_total: 0 });
  const [loading, setLoading] = useState(true);
  const [sel, setSel] = useState(new Set());
  const [allMatching, setAllMatching] = useState(false);
  const [confirm, setConfirm] = useState(null);
  const [deleting, setDeleting] = useState(false);
  const [open, setOpen] = useState(false);
  const [editing, setEditing] = useState(null);
  const [importOpen, setImportOpen] = useState(false);
  const catName = useMemo(() => Object.fromEntries(cats.map((c) => [c.id, c.name])), [cats]);
  const subName = useMemo(() => Object.fromEntries(subs.map((s) => [s.id, s.name])), [subs]);
  const active = { ...filters, search };

  const load = useCallback(() => {
    setLoading(true);
    return api.get("/admin/questions", { params: { page, page_size: size, ...active } })
      .then((r) => { setData(r.data); if (page > r.data.pages) setPage(r.data.pages); })
      .finally(() => setLoading(false));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [page, size, search, filters.category_id, filters.subject_id, filters.difficulty, filters.type]);
  useEffect(() => { load(); }, [load]);

  const clearSel = () => { setSel(new Set()); setAllMatching(false); };
  const setFilter = (k, v) => { setFilters((f) => ({ ...f, [k]: v, ...(k === "category_id" ? { subject_id: "" } : {}) })); setPage(1); clearSel(); };
  const pageIds = data.items.map((x) => x.id);
  const pageAll = pageIds.length > 0 && pageIds.every((id) => sel.has(id));
  const togglePage = () => { const n = new Set(sel); pageIds.forEach((id) => (pageAll ? n.delete(id) : n.add(id))); setSel(n); setAllMatching(false); };
  const toggle = (id) => { const n = new Set(sel); n.has(id) ? n.delete(id) : n.add(id); setSel(n); setAllMatching(false); };
  const count = allMatching ? data.total : sel.size;

  const doDelete = async () => {
    setDeleting(true);
    try {
      const body = confirm.single ? { ids: [confirm.single] } : allMatching ? { all_matching: true, filters: active } : { ids: [...sel] };
      const { data: r } = await api.post("/admin/questions/bulk-delete", body);
      toast.success(`Deleted ${r.deleted} question${r.deleted === 1 ? "" : "s"}`);
      if (!confirm.single) clearSel(); else { const n = new Set(sel); n.delete(confirm.single); setSel(n); }
      setConfirm(null);
      load();
    } catch (e) { toast.error(errMsg(e)); } finally { setDeleting(false); }
  };
  const saveQ = async (payload) => {
    if (editing?.id) await api.put(`/content/questions/${editing.id}`, payload); else await api.post("/questions", payload);
    toast.success(editing?.id ? "Changes saved" : "Created");
    load();
  };
  const from = data.total ? (page - 1) * size + 1 : 0;

  return (
    <div>
      <PageHeader eyebrow="Content" title="Question bank" desc={`${data.grand_total.toLocaleString()} questions in the bank.`}
                  action={<div className="flex flex-wrap gap-2">
                    <Button variant="outline" onClick={() => setImportOpen(true)} data-testid="import-questions-btn" className="border-gray-700 bg-transparent text-gray-200 hover:bg-gray-800"><Upload className="w-4 h-4 mr-1" />Import CSV / Excel</Button>
                    <NewButton onClick={() => { setEditing(null); setOpen(true); }} label="New question" testid="new-question-btn" />
                  </div>} />
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-3 mb-4">
        <input placeholder="Search questions…" value={filters.search} onChange={(e) => setFilter("search", e.target.value)} className={`${inputCls} mt-0`} data-testid="question-search" />
        <CategorySelect value={filters.category_id} onChange={(v) => setFilter("category_id", v)} categories={cats} allowAll testid="question-filter-category" />
        <SubjectSelect value={filters.subject_id} onChange={(v) => setFilter("subject_id", v)} subjects={subs} categoryId={filters.category_id} allowAll testid="question-filter-subject" />
        <select value={filters.difficulty} onChange={(e) => setFilter("difficulty", e.target.value)} className={inputCls} data-testid="question-filter-difficulty">
          <option value="">All difficulties</option><option value="easy">Easy</option><option value="medium">Medium</option><option value="hard">Hard</option>
        </select>
        <select value={filters.type} onChange={(e) => setFilter("type", e.target.value)} className={inputCls} data-testid="question-filter-type">
          <option value="">All types</option>{Object.entries(TYPE_LABEL).map(([k, v]) => <option key={k} value={k}>{v}</option>)}
        </select>
      </div>

      {count > 0 && (
        <div className="mb-3 flex flex-wrap items-center gap-3 rounded-md border border-blue-500/40 bg-blue-500/10 px-4 py-2.5 text-sm" data-testid="bulk-bar">
          <span className="text-white" data-testid="bulk-count">{count.toLocaleString()} selected</span>
          {pageAll && !allMatching && data.total > pageIds.length && (
            <button onClick={() => setAllMatching(true)} className="text-cyan-300 hover:underline" data-testid="select-all-matching">Select all {data.total.toLocaleString()} matching questions</button>
          )}
          <button onClick={clearSel} className="text-gray-400 hover:text-white" data-testid="clear-selection">Clear</button>
          <Button size="sm" onClick={() => setConfirm({})} className="ml-auto bg-rose-600 hover:bg-rose-700" data-testid="bulk-delete-btn"><Trash2 className="w-4 h-4 mr-1" />Delete selected</Button>
        </div>
      )}

      <DataTable head={[<input key="all" type="checkbox" checked={pageAll} onChange={togglePage} aria-label="Select page" data-testid="select-page" />, "Question", "Type", "Category", "Subject", "Level", "Marks", ""]}
                 testid="questions-table" empty={!loading && data.items.length === 0 ? "No questions match these filters." : null}>
        {data.items.map((x) => (
          <tr key={x.id} className={`border-t border-gray-800 hover:bg-gray-900/40 ${sel.has(x.id) || allMatching ? "bg-blue-500/5" : ""}`} data-testid={`question-row-${x.id}`}>
            <td className="p-3 w-8"><input type="checkbox" checked={allMatching || sel.has(x.id)} onChange={() => toggle(x.id)} data-testid={`select-q-${x.id}`} /></td>
            <td className="p-3 text-white max-w-md"><div className="line-clamp-2">{x.text}</div></td>
            <td className="p-3"><Pill tone="blue">{TYPE_LABEL[x.type]}</Pill></td>
            <td className="p-3 text-gray-400 whitespace-nowrap">{catName[x.category_id] || "—"}</td>
            <td className="p-3 text-gray-400 whitespace-nowrap" data-testid={`q-subject-${x.id}`}>{subName[x.subject_id] || "—"}</td>
            <td className="p-3"><Pill tone={DIFF_TONE[x.difficulty]}>{x.difficulty.toUpperCase()}</Pill></td>
            <td className="p-3 mono-font text-xs whitespace-nowrap"><span className="text-emerald-300">+{x.positive_marks}</span> <span className="text-rose-300">−{x.negative_marks}</span></td>
            <td className="p-3"><RowActions id={x.id} onEdit={() => { setEditing(x); setOpen(true); }} onDelete={() => setConfirm({ single: x.id })} /></td>
          </tr>
        ))}
      </DataTable>

      <div className="mt-4 flex flex-wrap items-center justify-between gap-3 text-sm text-gray-400" data-testid="pagination">
        <div className="flex items-center gap-2">
          Rows per page
          <select value={size} onChange={(e) => { setSize(Number(e.target.value)); setPage(1); clearSel(); }} className={`${inputCls} mt-0 w-24 py-1`} data-testid="page-size-select">
            {SIZES.map((n) => <option key={n} value={n}>{n}</option>)}
          </select>
          {loading && <Loader2 className="w-4 h-4 animate-spin" />}
        </div>
        <div className="flex items-center gap-3">
          <span data-testid="pagination-range">{from}–{Math.min(page * size, data.total)} of {data.total.toLocaleString()}</span>
          <button disabled={page <= 1} onClick={() => setPage(page - 1)} className="p-1.5 rounded border border-gray-800 hover:text-white disabled:opacity-30" data-testid="page-prev"><ChevronLeft className="w-4 h-4" /></button>
          <span className="mono-font text-xs" data-testid="page-indicator">{page} / {data.pages}</span>
          <button disabled={page >= data.pages} onClick={() => setPage(page + 1)} className="p-1.5 rounded border border-gray-800 hover:text-white disabled:opacity-30" data-testid="page-next"><ChevronRight className="w-4 h-4" /></button>
        </div>
      </div>

      <AlertDialog open={!!confirm} onOpenChange={(o) => !o && setConfirm(null)}>
        <AlertDialogContent className="bg-[#111827] border-gray-800 text-white" data-testid="delete-confirm-dialog">
          <AlertDialogHeader>
            <AlertDialogTitle>Delete {confirm?.single ? "this question" : `${count.toLocaleString()} question${count === 1 ? "" : "s"}`}?</AlertDialogTitle>
            <AlertDialogDescription className="text-gray-400">They'll also be removed from any tests that use them. This cannot be undone.</AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel className="bg-transparent border-gray-700 text-gray-200 hover:bg-gray-800" data-testid="delete-cancel">Cancel</AlertDialogCancel>
            <AlertDialogAction onClick={(e) => { e.preventDefault(); doDelete(); }} disabled={deleting} className="bg-rose-600 hover:bg-rose-700" data-testid="delete-confirm">
              {deleting ? <Loader2 className="w-4 h-4 animate-spin" /> : "Delete"}
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>

      <QuestionForm open={open} onOpenChange={setOpen} initial={editing} categories={cats} subjects={subs} onSave={saveQ} />
      <ImportDialog open={importOpen} onOpenChange={setImportOpen} categories={cats} subjects={subs} onImported={load} />
    </div>
  );
}
