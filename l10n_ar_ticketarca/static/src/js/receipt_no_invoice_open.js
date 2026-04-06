/** @odoo-module **/

import { ReceiptScreen } from "@point_of_sale/app/screens/receipt_screen/receipt_screen";
import { patch } from "@web/core/utils/patch";

patch(ReceiptScreen.prototype, {
    setup() {
        super.setup(...arguments);
        this.l10nArDisableInvoiceOpen = true;
    },

    async _downloadInvoice() {
        return null;
    },

    async downloadInvoice() {
        return null;
    },

    async onDownloadInvoice() {
        return null;
    },

    _shouldAutoDownloadInvoice() {
        return false;
    },

    shouldDownloadInvoice() {
        return false;
    },
});
