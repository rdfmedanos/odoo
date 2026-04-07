/** @odoo-module **/

import OrderPaymentValidation from "@point_of_sale/app/utils/order_payment_validation";
import { patch } from "@web/core/utils/patch";

patch(OrderPaymentValidation.prototype, {
    shouldDownloadInvoice() {
        return false;
    },

    async afterOrderValidation() {
        await super.afterOrderValidation();
        if (this.order.nb_print === 0) {
            await this.pos.printReceipt({ order: this.order });
        }
    },
});
