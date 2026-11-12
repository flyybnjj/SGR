(() => {
    'use strict';

    for (const board of document.querySelectorAll('[data-movable-board]')) {
        const cards = [...board.querySelectorAll('[data-card-stage]')].filter(card => card.querySelector('[data-board-move]'));
        if (!cards.length) continue;

        board.previousElementSibling.hidden = false;
        let activeCard = null;
        let highlighted = null;

        function highlight(column) {
            if (column === highlighted) return;
            highlighted?.classList.remove('is-drop-target');
            highlighted = column;
            highlighted?.classList.add('is-drop-target');
        }

        function reset() {
            activeCard?.classList.remove('is-dragging');
            activeCard = null;
            highlight(null);
        }

        function destination(event) {
            const column = event.target.closest('[data-board-stage]');
            return activeCard && column && column.dataset.boardStage !== activeCard.dataset.cardStage ? column : null;
        }

        for (const card of cards) {
            card.draggable = true;
            card.addEventListener('dragstart', event => {
                if (event.target !== card) {
                    event.preventDefault();
                    return;
                }
                activeCard = card;
                card.classList.add('is-dragging');
                event.dataTransfer.effectAllowed = 'move';
                event.dataTransfer.setData('text/plain', card.id);
            });
            card.addEventListener('dragend', reset);
        }

        board.addEventListener('dragover', event => {
            const column = destination(event);
            highlight(column);
            if (column) {
                event.preventDefault();
                event.dataTransfer.dropEffect = 'move';
            }
        });

        board.addEventListener('dragleave', event => {
            if (!board.contains(event.relatedTarget)) highlight(null);
        });

        board.addEventListener('drop', event => {
            const column = destination(event);
            if (!column) return;
            event.preventDefault();
            const target = column.dataset.boardStage;
            const form = activeCard.querySelector('[data-board-move]');
            reset();

            if (form.hasAttribute('data-needs-responsible') && target !== 'Ingresada') {
                const editor = new URL(form.dataset.moveEditor, location.href);
                editor.searchParams.set('mover', target);
                editor.hash = 'seguimiento';
                location.assign(editor);
                return;
            }
            form.querySelector('[data-board-destination]').value = target;
            form.requestSubmit();
        });
    }
})();
