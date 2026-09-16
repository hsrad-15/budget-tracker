/**
 * Lightweight mouse-tracked 3D tilt effect.
 * Attaches to any element with class "tilt-card". Respects reduced-motion.
 */
(function () {
    const prefersReducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
    if (prefersReducedMotion) return;

    function initTilt(el, options) {
        const maxTilt = options.maxTilt || 8;
        const scale = options.scale || 1.02;

        el.addEventListener('mousemove', (e) => {
            const rect = el.getBoundingClientRect();
            const x = e.clientX - rect.left;
            const y = e.clientY - rect.top;
            const centerX = rect.width / 2;
            const centerY = rect.height / 2;
            const rotateY = ((x - centerX) / centerX) * maxTilt;
            const rotateX = -((y - centerY) / centerY) * maxTilt;
            el.style.transform = `perspective(1000px) rotateX(${rotateX}deg) rotateY(${rotateY}deg) scale(${scale})`;
        });

        el.addEventListener('mouseleave', () => {
            el.style.transform = 'perspective(1000px) rotateX(0deg) rotateY(0deg) scale(1)';
        });
    }

    document.addEventListener('DOMContentLoaded', () => {
        document.querySelectorAll('.tilt-card').forEach((el) => {
            const maxTilt = parseFloat(el.dataset.maxTilt) || 8;
            const scale = parseFloat(el.dataset.tiltScale) || 1.02;
            initTilt(el, { maxTilt, scale });
        });
    });
})();
