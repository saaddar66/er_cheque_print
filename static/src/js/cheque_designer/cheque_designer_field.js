/** @odoo-module **/

import { registry } from "@web/core/registry";
import { Component, useRef, onMounted, onWillUnmount } from "@odoo/owl";
import { standardFieldProps } from "@web/views/fields/standard_field_props";

const FIELD_KEYS = [
    ["payee_name", "Payee Name"],
    ["amount_words_line1", "Amount Words L1"],
    ["amount_words_line2", "Amount Words L2"],
    ["amount_figures", "Amount Figures"],
    ["date", "Date"],
    ["account_title", "Account Title"],
    ["cheque_number", "Cheque Number"],
    ["memo", "Memo"],
    ["bank_name", "Bank Name"],
    ["bank_account_number", "Bank Acc Number"],
    ["bank_email", "Bank Email"],
    ["bank_address", "Bank Address"],
    ["payee_name_line1", "Payee Name L1"],
    ["payee_name_line2", "Payee Name L2"],
    ["account_payee", "Account Payee"]
];

export class ChequeDesignerField extends Component {
    static template = "er_cheque_print.ChequeDesignerField";
    static props = { ...standardFieldProps };

    setup() {
        this.canvasRef = useRef("canvas");
        this.FIELD_KEYS = FIELD_KEYS;
        this._draggingRecord = null;
        this._resizeObserver = null;

        this._onPointerMove = (ev) => this.onPointerMove(ev);
        this._onPointerUp = () => this.onPointerUp();

        onMounted(() => {
            window.addEventListener("pointermove", this._onPointerMove);
            window.addEventListener("pointerup", this._onPointerUp);

            // Recompute the canvas height any time its actual rendered
            // width changes - covers the case where this field mounts
            // while its notebook page is hidden (offsetWidth === 0 at
            // mount time), window resizes, or the sheet finishes laying
            // out after mount. A single onMounted read is not reliable
            // because a hidden tab reports 0 width, which previously
            // locked the canvas height at 0px forever.
            this._resizeObserver = new ResizeObserver(() => this._enforceAspectRatio());
            this._resizeObserver.observe(this.canvasRef.el);

            // Also try immediately in case the canvas is already visible.
            this._enforceAspectRatio();
        });
        onWillUnmount(() => {
            window.removeEventListener("pointermove", this._onPointerMove);
            window.removeEventListener("pointerup", this._onPointerUp);
            this._resizeObserver?.disconnect();
        });
    }

    /**
     * Lock the canvas height so its aspect ratio exactly matches
     * cheque_width_mm : cheque_height_mm.  This guarantees that a chip
     * positioned at (pos_x%, pos_y%) in the designer lands at the same
     * relative position inside the cheque div in the QWeb PDF template.
     *
     * Without this, the canvas height was determined by the uploaded
     * reference image's natural pixel dimensions - which almost never
     * matched the cheque mm ratio - causing every Y position to be wrong
     * on the printed output.
     *
     * Guards against offsetWidth being 0 (e.g. canvas is inside a
     * currently-hidden notebook page) so we never lock in a 0px height;
     * the ResizeObserver set up in onMounted will call this again once
     * the canvas actually has real dimensions.
     */
    _enforceAspectRatio() {
        const canvas = this.canvasRef.el;
        if (!canvas || !canvas.offsetWidth) {
            return;
        }
        const rec = this.props.record.data;
        const widthMm = rec.cheque_width_mm || 210;
        const heightMm = rec.cheque_height_mm || 75;
        const ratio = heightMm / widthMm;          // e.g. 75/210 ~= 0.357
        canvas.style.height = (canvas.offsetWidth * ratio) + "px";
    }

    get list() {
        return this.props.record.data[this.props.name];
    }

    get records() {
        return this.list.records;
    }

    get imageUrl() {
        const imageFieldName = this.props.options?.image_field || "reference_image";
        const record = this.props.record;
        const imageData = record.data[imageFieldName];

        if (!imageData) {
            return "";
        }

        // Once the record is saved, don't trust record.data for the binary
        // value - attachment=True binary fields are not guaranteed to come
        // back from the server as full base64 on a reload/re-read (this is
        // exactly why the standard built-in "image" widget switches to a
        // URL-based src for saved records instead of embedding base64).
        // Relying on record.data here is what made the image vanish right
        // after pressing Save. Use the binary controller URL instead, with
        // a cache-busting param so edits/re-uploads show up immediately.
        if (record.resId) {
            const cacheBust = record.data.write_date
                ? encodeURIComponent(record.data.write_date)
                : Date.now();
            return `/web/image/${record.resModel}/${record.resId}/${imageFieldName}?unique=${cacheBust}`;
        }

        // New/unsaved record: no res_id yet, so there is no controller URL
        // to fetch from. imageData here is the raw base64 string that was
        // just uploaded and is sitting in local memory - use it directly.
        return `data:image/png;base64,${imageData}`;
    }

    onPointerDownChip(ev, record) {
        ev.preventDefault();
        ev.stopPropagation();
        this._draggingRecord = record;
    }

    onPointerMove(ev) {
        if (!this._draggingRecord || !this.canvasRef.el) {
            return;
        }
        const rect = this.canvasRef.el.getBoundingClientRect();
        let x = ((ev.clientX - rect.left) / rect.width) * 100;
        let y = ((ev.clientY - rect.top) / rect.height) * 100;
        x = Math.min(100, Math.max(0, x));
        y = Math.min(100, Math.max(0, y));
        this._draggingRecord.update({ pos_x: x, pos_y: y });
    }

    onPointerUp() {
        this._draggingRecord = null;
    }

    async addField(fieldKey) {
        await this.list.addNewRecord({ position: "bottom" });
        const newRecord = this.records[this.records.length - 1];
        await newRecord.update({ field_key: fieldKey, pos_x: 40, pos_y: 40 });
    }

    async removeField(record) {
        // Deleting must go through the parent list, not the record itself.
        // record.delete() bypasses the list's new-vs-saved bookkeeping and
        // falls through to a raw unlink() call using record.resId - which
        // is `false` for a chip that was just added via addField() and
        // never saved, causing "Invalid ids list: false". list.delete()
        // correctly just drops unsaved records locally, and queues a
        // proper unlink command only for already-persisted rows.
        await this.list.delete(record.id);
    }
}

registry.category("fields").add("cheque_designer", {
    component: ChequeDesignerField,
});