/** @odoo-module **/

import { Order } from "@point_of_sale/app/store/models";
import { patch } from "@web/core/utils/patch";

patch(Order.prototype, {
    export_for_printing() {
        const receipt = super.export_for_printing(...arguments);
        let paperWidth = "80";
        if (
            this.pos &&
            this.pos.config &&
            this.pos.config.l10n_ar_ticketarca_paper_width
        ) {
            paperWidth = this.pos.config.l10n_ar_ticketarca_paper_width;
        }
        receipt.l10n_ar_ticketarca_paper_width = paperWidth;

        if (this.l10nArAfipData && this.l10nArAfipData.cae) {
            receipt.l10n_ar_afip = this.l10nArAfipData;
        }
        return receipt;
    },
});
