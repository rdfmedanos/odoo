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
            const order = this.pos.get_order();
            if (!order || !order.server_id) {
                return;
            }

            try {
                const afipData = await this.orm.call(
                    "pos.order",
                    "l10n_ar_get_ticket_afip_data",
                    [order.server_id]
                );

                if (afipData && afipData.cae) {
                    order.l10nArAfipData = afipData;
                }
            } catch {
                order.l10nArAfipData = null;
            }
        });
    },
});
