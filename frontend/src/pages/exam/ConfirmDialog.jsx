import React from "react";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from "../../components/ui/dialog";
import { Button } from "../../components/ui/button";
import { StatBoxes } from "./Palette";

export default function ConfirmDialog({ kind, onClose, onConfirm, stats, sectionName, nextSectionName }) {
  const section = kind === "section";
  return (
    <Dialog open={!!kind} onOpenChange={(o) => !o && onClose()}>
      <DialogContent className="bg-[#0b1120] border-gray-800 text-white" data-testid="exam-confirm-dialog">
        <DialogHeader>
          <DialogTitle className="heading-font">{section ? `Submit ${sectionName}?` : "Submit the test?"}</DialogTitle>
        </DialogHeader>
        <div className="text-sm text-gray-300 space-y-3">
          <StatBoxes stats={stats} />
          <p>
            {section
              ? `You can't come back to ${sectionName} after this. ${nextSectionName} starts immediately with its own timer.`
              : "Once submitted you can't change your responses. Review your palette first."}
          </p>
        </div>
        <DialogFooter>
          <Button variant="outline" onClick={onClose} className="border-gray-700 bg-transparent text-gray-200">Review again</Button>
          <Button onClick={onConfirm} data-testid="exam-confirm-submit" className={section ? "bg-violet-600 hover:bg-violet-700" : "bg-rose-600 hover:bg-rose-700"}>
            {section ? "Start next section" : "Submit now"}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
