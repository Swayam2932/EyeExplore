document.addEventListener('DOMContentLoaded', () => {
    // We attach mousedown to document because Dash components might mount later
    document.addEventListener('mousedown', function(e) {
        const divider = document.getElementById('drag-divider');
        
        // Check if the click is on the divider or inside it
        if (divider && (e.target === divider || divider.contains(e.target))) {
            e.preventDefault();
            
            const leftPanel = document.getElementById('left-panel');
            const rightPanel = document.getElementById('right-panel');
            const container = document.getElementById('split-container');
            
            if (!leftPanel || !rightPanel || !container) return;
            
            let isDragging = true;
            
            // Visual active state for divider
            divider.style.backgroundColor = '#3f51b5'; // blue highlight
            
            // We overlay a transparent div across the whole screen to capture mouse events.
            // This prevents iframes/graphs from swallowing mousemove events during drag.
            const overlay = document.createElement('div');
            overlay.style.position = 'fixed';
            overlay.style.top = '0';
            overlay.style.left = '0';
            overlay.style.width = '100vw';
            overlay.style.height = '100vh';
            overlay.style.zIndex = '9999';
            overlay.style.cursor = 'col-resize';
            document.body.appendChild(overlay);

            function onMouseMove(e) {
                if (!isDragging) return;
                
                const containerRect = container.getBoundingClientRect();
                
                // Mouse position relative to the container
                let newLeftWidth = e.clientX - containerRect.left;
                
                // Enforce minimum width (e.g., 10%)
                const minWidth = containerRect.width * 0.1;
                const maxWidth = containerRect.width * 0.9;
                
                if (newLeftWidth < minWidth) newLeftWidth = minWidth;
                if (newLeftWidth > maxWidth) newLeftWidth = maxWidth;
                
                const percentage = (newLeftWidth / containerRect.width) * 100;
                
                // Update flex-basis using CSS variables on the document root so React doesn't wipe them out
                document.documentElement.style.setProperty('--left-panel-flex', `0 0 calc(${percentage}% - 8px)`);
                document.documentElement.style.setProperty('--right-panel-flex', `0 0 calc(${100 - percentage}% - 8px)`);
                
                // Also update the elements directly to ensure immediate feedback
                leftPanel.style.flex = `var(--left-panel-flex)`;
                rightPanel.style.flex = `var(--right-panel-flex)`;
                
                // Dispatch resize event so Plotly redraws responsively
                window.dispatchEvent(new Event('resize'));
            }
            
            function onMouseUp(e) {
                isDragging = false;
                
                if (divider) {
                    divider.style.backgroundColor = '#e8e8e8'; // restore color
                }
                
                if (overlay.parentNode) {
                    overlay.parentNode.removeChild(overlay);
                }
                
                document.removeEventListener('mousemove', onMouseMove);
                document.removeEventListener('mouseup', onMouseUp);
                
                // Final resize event after drag ends
                setTimeout(() => window.dispatchEvent(new Event('resize')), 100);
            }
            
            document.addEventListener('mousemove', onMouseMove);
            document.addEventListener('mouseup', onMouseUp);
        }
    });
});
