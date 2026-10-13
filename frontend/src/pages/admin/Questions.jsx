import React, { useMemo, useState } from "react";
import { PageHeader, DataTable, Pill, RowActions, NewButton, inputCls, CategorySelect, useResource, useCategories } from "../../components/admin/kit";
import QuestionForm from "./QuestionForm";
import ImportDialog from "./ImportDialog";
import { Button } from "../../components/ui/button";
import { Upload } from "lucide-react";

const TYPE_LABEL = { mcq_single: "MCQ", mcq_multi: "MULTI", true_false: "T/F", numerical: "NUM" };
const DIFF_TONE = { easy: "emerald", medium: "amber", hard: "rose" };

export default function Questions() {
  const { items, loading, reload, save, remove } = useResource("/questions", "questions");
  const [importOpen, setImportOpen] = useState(false);
  const cats = useCategories();
  const [q, setQ] = useState("");
  const [cat, setCat] = useState("");
  const [diff, setDiff] = useState("");
  const [open, setOpen] = useState(false);
  const [editing, setEditing] = useState(null);
  const catName = useMemo(() => Object.fromEntries(cats.map((c) => [c.id, c.name])), [cats]);

  const rows = items.filter((x) =>
    (!cat || x.category_id === cat) && (!diff || x.difficulty === diff) && x.text.toLowerCase().includes(q.toLowerCase()));

  const openForm = (item) => { setEditing(item); setOpen(true); };

  return (
    <div>
      <PageHeader eyebrow="Content" title="Question bank" desc={`${items.length} questions available for tests.`}
                  action={<div className="flex gap-2">
                    <Button variant="outline" onClick={() => setImportOpen(true)} data-testid="import-questions-btn" className="border-gray-700 bg-transparent text-gray-200 hover:bg-gray-800"><Upload className="w-4 h-4 mr-1" />Import CSV / Excel</Button>
                    <NewButton onClick={() => openForm(null)} label="New question" testid="new-question-btn" />
                  </div>} />
      <div className="grid sm:grid-cols-3 gap-3 mb-4">
        <input placeholder="Search questions…" value={q} onChange={(e) => setQ(e.target.value)} className={inputCls} data-testid="question-search" />
        <CategorySelect value={cat} onChange={setCat} categories={cats} allowAll testid="question-filter-category" />
        <select value={diff} onChange={(e) => setDiff(e.target.value)} className={inputCls} data-testid="question-filter-difficulty">
          <option value="">All difficulties</option><option value="easy">Easy</option><option value="medium">Medium</option><option value="hard">Hard</option>
        </select>
      </div>
      <DataTable head={["Question", "Type", "Category", "Level", "Marks", ""]} testid="questions-table"
                 empty={!loading && rows.length === 0 ? "No questions match these filters." : null}>
        {rows.map((x) => (
          <tr key={x.id} className="border-t border-gray-800 hover:bg-gray-900/40" data-testid={`question-row-${x.id}`}>
            <td className="p-3 text-white max-w-md"><div className="line-clamp-2">{x.text}</div></td>
            <td className="p-3"><Pill tone="blue">{TYPE_LABEL[x.type]}</Pill></td>
            <td className="p-3 text-gray-400 whitespace-nowrap">{catName[x.category_id] || "—"}</td>
            <td className="p-3"><Pill tone={DIFF_TONE[x.difficulty]}>{x.difficulty.toUpperCase()}</Pill></td>
            <td className="p-3 mono-font text-xs whitespace-nowrap"><span className="text-emerald-300">+{x.positive_marks}</span> <span className="text-rose-300">−{x.negative_marks}</span></td>
            <td className="p-3"><RowActions id={x.id} onEdit={() => openForm(x)} onDelete={() => remove(x.id)} /></td>
          </tr>
        ))}
      </DataTable>
      <QuestionForm open={open} onOpenChange={setOpen} initial={editing} categories={cats}
                    onSave={(payload) => save(editing?.id, payload, "/questions")} />
      <ImportDialog open={importOpen} onOpenChange={setImportOpen} categories={cats} onImported={reload} />
    </div>
  );
}
