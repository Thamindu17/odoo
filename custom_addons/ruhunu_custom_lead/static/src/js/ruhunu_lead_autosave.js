/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { FormController } from "@web/views/form/form_controller";
import { onPatched, useEffect } from "@odoo/owl";

/**
 * Ruhunu Custom Lead — Auto-save patch for crm.lead form views.
 *
 * Behaviour
 * ─────────
 * • Debounced (1.5 s) auto-save on every field change.
 * • Scope guard: only crm.lead forms are affected.
 * • New-record guard: skipped until the record has been saved once.
 * • One2many editing guard: auto-save paused while a list row is open,
 *   so the product dropdown is never destroyed mid-selection.
 * • Files button guard: clicking the paperclip while the form is dirty
 *   triggers an IMMEDIATE save, then re-fires the click via a re-entrance
 *   flag so the handler does not enter an infinite save loop.
 */
patch(FormController.prototype, {
    setup() {
        super.setup();
        this._ruhunuAutoSaveTimer = null;

        // ── Auto-save on field changes ─────────────────────────────────────
        onPatched(() => {
            if (this.props.resModel !== "crm.lead") return;
            const root = this.model && this.model.root;
            if (!root || !root.isDirty || root.isNew) return;
            if (this._ruhunuHasActiveListRow(root)) {
                clearTimeout(this._ruhunuAutoSaveTimer);
                this._ruhunuAutoSaveTimer = null;
                return;
            }
            this._ruhunuScheduleAutoSave();
        });

        // ── Immediate save before "Files" button action fires ──────────────
        //
        // Using a closure-scoped isHandling flag to prevent infinite loops:
        //   • Computed fields (e.g. _compute_expected_revenue) can mark the
        //     record dirty again immediately after root.save() completes.
        //   • Without the flag, btn.click() would re-enter this handler,
        //     find isDirty=true, save again, click again — infinite loop.
        //   • With isHandling=true set BEFORE btn.click(), the re-triggered
        //     click skips interception and passes straight through to OWL.
        useEffect(() => {
            let isHandling = false;

            const handleAttachmentClick = async (e) => {
                if (this.props.resModel !== "crm.lead") return;

                const btn = e.target.closest(
                    'button[name="action_manage_attachments"]'
                );
                if (!btn) return;

                // Re-entrance guard: let the programmatic re-click through.
                if (isHandling) return;

                const root = this.model && this.model.root;
                if (!root || root.isNew || !root.isDirty) return;

                // Dirty form — block original click, save, then re-fire.
                e.stopImmediatePropagation();
                e.preventDefault();

                clearTimeout(this._ruhunuAutoSaveTimer);
                this._ruhunuAutoSaveTimer = null;

                isHandling = true;
                try {
                    await root.save();
                } catch (_err) {
                    // Validation error already shown by Odoo.
                    // Do NOT open the attachments dialog.
                    isHandling = false;
                    return;
                }

                // isHandling is still true — the re-triggered click will
                // return immediately at the guard above and pass through
                // to OWL's own handlers normally.
                btn.click();
                isHandling = false;
            };

            document.addEventListener("click", handleAttachmentClick, true);
            return () => {
                document.removeEventListener("click", handleAttachmentClick, true);
            };
        }, () => []); // Register once on mount, clean up on unmount.
    },

    /**
     * Returns true if any One2many list on the record has a row in edit mode.
     * @private
     */
    _ruhunuHasActiveListRow(root) {
        try {
            for (const fieldName in root.fields) {
                if (root.fields[fieldName].type !== "one2many") continue;
                const list = root.data[fieldName];
                if (list && list.editedRecord) return true;
            }
        } catch (_e) { /* never crash the form */ }
        return false;
    },

    /**
     * Debounced auto-save — collapses rapid edits into one RPC.
     * @private
     */
    _ruhunuScheduleAutoSave() {
        clearTimeout(this._ruhunuAutoSaveTimer);
        this._ruhunuAutoSaveTimer = setTimeout(async () => {
            const root = this.model && this.model.root;
            if (!root || !root.isDirty || root.isNew) return;
            if (this._ruhunuHasActiveListRow(root)) return;
            try {
                await root.save();
            } catch (_err) { /* Odoo shows validation errors to the user */ }
        }, 1500);
    },
});
