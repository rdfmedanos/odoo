/** @odoo-module **/

import { onWillStart } from "@odoo/owl";
import { ReceiptScreen } from "@point_of_sale/app/screens/receipt_screen/receipt_screen";
import { patch } from "@web/core/utils/patch";
import { useService } from "@web/core/utils/hooks";

patch(ReceiptScreen.prototype, {
    setup() {
        super.setup(...arguments);
        this.l10nArTicketArcaOrm = useService("orm");

        onWillStart(async () => {
            try {
                const order = this.currentOrder;
                if (!order || !order.uuid) {
                    return;
                }
                const afipData = await this.l10nArTicketArcaOrm.call(
                    "pos.order",
                    "l10n_ar_get_ticket_afip_data_by_uuid",
                    [order.uuid]
                );
                order.l10n_ar_afip_data = afipData || null;
            } catch (error) {
                this.currentOrder.l10n_ar_afip_data = null;
            }
        });
    },
});
