// clinic/static/clinic/js/main.js

let doctorsScrollPosition = 0;
let clinicsScrollPosition = 0;

function scrollDoctors(direction) {
    const wrapper = document.getElementById('doctors-wrapper');
    const cardWidth = 250 + 16; // ширина карточки + отступ
    const step = direction * cardWidth;

    doctorsScrollPosition += step;
    wrapper.scrollLeft = doctorsScrollPosition;
}

function scrollClinics(direction) {
    const wrapper = document.getElementById('clinics-wrapper');
    const cardWidth = 250 + 16;
    const step = direction * cardWidth;

    clinicsScrollPosition += step;
    wrapper.scrollLeft = clinicsScrollPosition;
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
}

// Инициализация: скролл в начало
document.addEventListener('DOMContentLoaded', () => {
    const doctorsWrapper = document.getElementById('doctors-wrapper');
    const clinicsWrapper = document.getElementById('clinics-wrapper');

    // Устанавливаем начальную позицию скролла
    doctorsScrollPosition = 0;
    clinicsScrollPosition = 0;

    // Пример: автоматический скролл через 3 секунды (опционально)
    // setTimeout(() => {
    //     scrollDoctors(1);
    // }, 3000);
});