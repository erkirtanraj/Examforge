import React, { useRef, useState } from "react";
import { toast } from "sonner";
import { Upload, Loader2, X, ImageIcon } from "lucide-react";
import { api, assetUrl } from "../../lib/api";
import { Field, inputCls, errMsg } from "./kit";

// Image setting: upload to the server or paste a URL, with live preview.
export default function ImageField({ label, value, onChange, testid, hint, wide = false }) {
  const ref = useRef(null);
  const [busy, setBusy] = useState(false);
  const upload = async (file) => {
    if (!file) return;
    if (file.size > 2 * 1024 * 1024) return toast.error("Image must be 2 MB or smaller");
    setBusy(true);
    try {
      const fd = new FormData();
      fd.append("file", file);
      const { data } = await api.post("/admin/uploads", fd);
      onChange(data.url);
      toast.success("Uploaded — click Save to apply");
    } catch (e) { toast.error(errMsg(e)); }
    finally { setBusy(false); if (ref.current) ref.current.value = ""; }
  };
  return (
    <Field label={label}>
      <div className="mt-1.5 flex flex-col sm:flex-row gap-3 sm:items-center">
        <div className={`${wide ? "w-40 h-[90px]" : "w-20 h-20"} shrink-0 rounded-md border border-gray-800 bg-[#0b1120] flex items-center justify-center overflow-hidden`} data-testid={`${testid}-preview`}>
          {value ? <img src={assetUrl(value)} alt="" className={wide ? "w-full h-full object-cover" : "max-w-full max-h-full object-contain"} /> : <ImageIcon className="w-6 h-6 text-gray-600" />}
        </div>
        <div className="flex-1 min-w-0 space-y-2">
          <input value={value} onChange={(e) => onChange(e.target.value)} placeholder="https://… or upload a file" className={`${inputCls} mt-0 mono-font text-xs`} data-testid={`${testid}-url`} />
          <div className="flex flex-wrap gap-2">
            <input ref={ref} type="file" accept="image/png,image/jpeg,image/webp,image/gif,image/svg+xml,image/x-icon,.ico" hidden onChange={(e) => upload(e.target.files?.[0])} data-testid={`${testid}-file`} />
            <button type="button" onClick={() => ref.current?.click()} disabled={busy} className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-md border border-gray-700 text-gray-200 text-xs hover:bg-gray-800 disabled:opacity-50" data-testid={`${testid}-upload`}>
              {busy ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Upload className="w-3.5 h-3.5" />} Upload
            </button>
            {value && (
              <button type="button" onClick={() => onChange("")} className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-md border border-gray-700 text-gray-300 text-xs hover:text-rose-300 hover:border-rose-500/40" data-testid={`${testid}-remove`}>
                <X className="w-3.5 h-3.5" /> Remove
              </button>
            )}
          </div>
          {hint && <p className="text-[11px] text-gray-500 normal-case tracking-normal font-sans">{hint}</p>}
        </div>
      </div>
    </Field>
  );
}
