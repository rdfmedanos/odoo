/** @odoo-module **/

const CART_LINK_SELECTOR = [
    '.modal a[href*="/shop/cart"]',
    '.modal button[href*="/shop/cart"]',
    '.modal-footer a[href*="/shop/cart"]',
    '.modal-footer button[href*="/shop/cart"]',
    '.offcanvas a[href*="/shop/cart"]',
].join(',');

function styleCartLinks(root = document) {
    for (const element of root.querySelectorAll(CART_LINK_SELECTOR)) {
        element.classList.remove('btn-link', 'btn-light', 'btn-secondary', 'btn-outline-secondary');
        element.classList.add('btn', 'art-btn');
        element.style.background = 'linear-gradient(135deg, var(--color-fucsia) 0%, var(--color-violeta) 100%)';
        element.style.color = '#fff';
        element.style.border = 'none';
        element.style.boxShadow = '0 12px 26px rgba(225, 45, 123, 0.18)';
        element.style.textDecoration = 'none';
        element.style.borderRadius = '999px';
        element.style.padding = '0.75rem 1.4rem';
        element.style.fontWeight = '700';
        element.style.width = element.classList.contains('w-100') ? '100%' : element.style.width;
    }
}

function startObserver() {
    styleCartLinks();

    const observer = new MutationObserver((mutations) => {
        for (const mutation of mutations) {
            for (const node of mutation.addedNodes) {
                if (!(node instanceof Element)) {
                    continue;
                }
                if (node.matches?.(CART_LINK_SELECTOR)) {
                    styleCartLinks(node.parentElement || document);
                    continue;
                }
                if (node.querySelector?.(CART_LINK_SELECTOR)) {
                    styleCartLinks(node);
                }
            }
        }
    });

    observer.observe(document.body, { childList: true, subtree: true });
}

if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', startObserver, { once: true });
} else {
    startObserver();
}
