/** @odoo-module **/

import { onWillStart } from "@odoo/owl";
import { ReceiptScreen } from "@point_of_sale/app/screens/receipt_screen/receipt_screen";
import { patch } from "@web/core/utils/patch";
import { useService } from "@web/core/utils/hooks";

patch(ReceiptScreen.prototype, {
    setup() {
        super.setup();
        this.orm = useService("orm");

        onWillStart(async () => {
            try {
                const pos = this.pos;
                if (!pos || !pos.get_order) {
                    return;
                }

                const order = pos.get_order();
                if (!order || !order.server_id) {
                    return;
                }

                const afipData = await this.orm.call(
                    "pos.order",
                    "l10n_ar_get_ticket_afip_data",
                    [order.server_id]
                );

                if (afipData && afipData.cae) {
                    order.l10nArAfipData = afipData;
                }
            } catch (error) {
                order.l10nArAfipData = null;
            }
        });
    },

    async _downloadInvoice() {
        return true;
    },

    async downloadInvoice() {
        return true;
    },
});
