import React, { useState } from "react";
import { Award, Download, Loader2, Lock, ExternalLink } from "lucide-react";
import { Link } from "react-router-dom";
import { toast } from "sonner";
import { api } from "../lib/api";
import { useSite } from "../lib/site";
import { downloadCertificate } from "../lib/certificate";
import { errMsg } from "./admin/kit";
import { Button } from "./ui/button";

export default function CertificateCard({ course, progress, cert, onIssued }) {
  const { site } = useSite();
  const [busy, setBusy] = useState(false);
  const finished = progress.total > 0 && progress.completed >= progress.total;
  const get = async () => {
    setBusy(true);
    try {
      const c = cert || (await api.post(`/courses/${course.id}/certificate`)).data;
      onIssued(c);
      downloadCertificate(c, { brand: site?.header?.brand_name, primary: site?.theme?.primary, accent: site?.theme?.accent, verifyUrl: `${window.location.origin}/verify/${c.id}` });
    } catch (e) { toast.error(errMsg(e)); } finally { setBusy(false); }
  };
  return (
    <div className={`card-elev p-4 ${finished ? "border-amber-400/40" : ""}`} data-testid="certificate-card">
      <div className="flex items-start gap-3">
        <div className={`w-10 h-10 rounded-lg flex items-center justify-center shrink-0 ${finished ? "bg-amber-400/15 text-amber-300" : "bg-gray-800 text-gray-500"}`}>
          {finished ? <Award className="w-5 h-5" /> : <Lock className="w-5 h-5" />}
        </div>
        <div className="min-w-0 flex-1">
          <div className="heading-font text-sm font-semibold text-white">Certificate of completion</div>
          <p className="text-xs text-gray-400 mt-0.5" data-testid="certificate-status">
            {finished ? (cert ? `Issued · ID ${cert.id}` : "You've finished every lesson — claim your certificate.") : `Finish all ${progress.total} lessons to unlock (${progress.completed} done).`}
          </p>
        </div>
      </div>
      {finished && (
        <div className="mt-3 flex flex-wrap items-center gap-3">
          <Button size="sm" onClick={get} disabled={busy} className="bg-amber-500 hover:bg-amber-600 text-black" data-testid="certificate-download">
            {busy ? <Loader2 className="w-4 h-4 animate-spin" /> : <><Download className="w-4 h-4 mr-1" />{cert ? "Download PDF" : "Get certificate"}</>}
          </Button>
          {cert && <Link to={`/verify/${cert.id}`} className="text-xs text-blue-400 hover:text-blue-300 inline-flex items-center gap-1" data-testid="certificate-verify-link">Verify<ExternalLink className="w-3 h-3" /></Link>}
        </div>
      )}
    </div>
  );
}
