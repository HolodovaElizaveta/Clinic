// Ширина одной карточки + отступ справа (1.8rem ≈ 28.8px)
const CARD_WIDTH = 280 + 28.8;

// Добавим функцию для обновления точек индикации
function updateDots(wrapperId, dotsContainerId) {
    const wrapper = document.getElementById(wrapperId);
    const dotsContainer = document.getElementById(dotsContainerId);
    if (!wrapper || !dotsContainer) return;

    const totalCards = wrapper.children.length;
    const visibleCards = 3; // всегда показываем 3
    const maxScroll = wrapper.scrollWidth - wrapper.clientWidth;

    let currentSlide = Math.round(wrapper.scrollLeft / CARD_WIDTH);

    // Пересчитаем количество точек
    const dotsCount = Math.ceil(totalCards / visibleCards);
    dotsContainer.innerHTML = '';

    for (let i = 0; i < dotsCount; i++) {
        const dot = document.createElement('div');
        dot.className = `carousel-dot ${i === currentSlide ? 'active' : ''}`;
        dot.addEventListener('click', () => {
            const targetScroll = i * CARD_WIDTH * visibleCards;
            wrapper.scrollTo({
                left: targetScroll,
                behavior: 'smooth'
            });
        });
        dotsContainer.appendChild(dot);
    }
}

function scrollDoctors(direction) {
    const wrapper = document.getElementById('doctors-wrapper');
    if (!wrapper) return;

    const currentScroll = wrapper.scrollLeft;
    const newPosition = currentScroll + direction * CARD_WIDTH;
    wrapper.scrollTo({
        left: newPosition,
        behavior: 'smooth'
    });

    setTimeout(() => updateDots('doctors-wrapper', 'doctors-dots'), 300);
}

function scrollClinics(direction) {
    const wrapper = document.getElementById('clinics-wrapper');
    if (!wrapper) return;

    const currentScroll = wrapper.scrollLeft;
    const newPosition = currentScroll + direction * CARD_WIDTH;
    wrapper.scrollTo({
        left: newPosition,
        behavior: 'smooth'
    });

    setTimeout(() => updateDots('clinics-wrapper', 'clinics-dots'), 300);
}

function filterDoctors() {
    const filterValue = document.getElementById('specialization-filter').value;
    const cards = document.querySelectorAll('.doctor-card');

    cards.forEach(card => {
        if (filterValue === '' || card.dataset.specialization === filterValue) {
            card.style.display = 'flex';
        } else {
            card.style.display = 'none';
        }
    });

    // После фильтрации обновляем позицию и точки
    const wrapper = document.getElementById('doctors-wrapper');
    if (wrapper) {
        wrapper.scrollLeft = 0;
        setTimeout(() => updateDots('doctors-wrapper', 'doctors-dots'), 300);
    }
}

document.addEventListener('DOMContentLoaded', () => {
    const doctorsWrapper = document.getElementById('doctors-wrapper');
    const clinicsWrapper = document.getElementById('clinics-wrapper');

    if (doctorsWrapper) {
        doctorsWrapper.scrollLeft = 0;
        updateDots('doctors-wrapper', 'doctors-dots');
    }

    if (clinicsWrapper) {
        clinicsWrapper.scrollLeft = 0;
        updateDots('clinics-wrapper', 'clinics-dots');
    }

    // При изменении размера окна — обновляем точки
    window.addEventListener('resize', () => {
        if (doctorsWrapper) updateDots('doctors-wrapper', 'doctors-dots');
        if (clinicsWrapper) updateDots('clinics-wrapper', 'clinics-dots');
    });
});