// Инициализируем данные для графиков
let resourceChart;
const maxDataPoints = 30;

// При загрузке документа
$(document).ready(function() {
    // Инициализация WebSocket
    const socket = io();
    
    // Инициализация графика ресурсов
    const ctx = document.getElementById('resourceChart').getContext('2d');
    resourceChart = new Chart(ctx, {
        type: 'line',
        data: {
            labels: [], // Будем заполнять динамически
            datasets: [
                {
                    label: 'CPU %',
                    data: [],
                    borderColor: 'rgba(13, 110, 253, 1)',
                    backgroundColor: 'rgba(13, 110, 253, 0.1)',
                    borderWidth: 2,
                    fill: true,
                    tension: 0.4
                },
                {
                    label: 'Память %',
                    data: [],
                    borderColor: 'rgba(25, 135, 84, 1)',
                    backgroundColor: 'rgba(25, 135, 84, 0.1)',
                    borderWidth: 2,
                    fill: true,
                    tension: 0.4
                }
            ]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            scales: {
                y: {
                    beginAtZero: true,
                    max: 100,
                    title: {
                        display: true,
                        text: 'Использование (%)'
                    }
                },
                x: {
                    title: {
                        display: true,
                        text: 'Время'
                    }
                }
            },
            animation: {
                duration: 300
            },
            plugins: {
                legend: {
                    position: 'top',
                },
                tooltip: {
                    mode: 'index',
                    intersect: false
                }
            }
        }
    });

    // Функция обновления статистики ресурсов
    function updateSystemStats(stats) {
        // Обновление значений CPU
        $('#cpu-value').text(stats.cpu_percent.toFixed(1) + '%');
        $('#cpu-progress').css('width', stats.cpu_percent + '%');
        
        // Обновление значений памяти
        $('#memory-value').text(stats.memory_percent.toFixed(1) + '%');
        $('#memory-used').text(stats.memory_used.toFixed(1));
        $('#memory-total').text(stats.memory_total.toFixed(1));
        $('#memory-progress').css('width', stats.memory_percent + '%');
        
        // Обновление значений сети
        $('#network-value').text(stats.net_recv.toFixed(1) + ' МБ');
        $('#network-recv').text(stats.net_recv.toFixed(1));
        $('#network-progress').css('width', Math.min(stats.net_recv / 10 * 100, 100) + '%'); // 10 МБ = 100%
        
        // Подсветка высокой нагрузки
        $('#cpu-card').toggleClass('high-usage', stats.cpu_percent > 80);
        $('#memory-card').toggleClass('high-usage', stats.memory_percent > 80);
        
        // Анимация обновления данных
        $('.stats-value').addClass('highlight');
        setTimeout(() => $('.stats-value').removeClass('highlight'), 2000);
        
        // Обновление графика
        resourceChart.data.labels.push(stats.timestamp);
        resourceChart.data.datasets[0].data.push(stats.cpu_percent);
        resourceChart.data.datasets[1].data.push(stats.memory_percent);
        
        // Ограничиваем количество точек на графике
        if (resourceChart.data.labels.length > maxDataPoints) {
            resourceChart.data.labels.shift();
            resourceChart.data.datasets.forEach(dataset => {
                dataset.data.shift();
            });
        }
        
        resourceChart.update();
    }

    // Функция обновления статистики раздач
    function updateRaffleStats(stats) {
        $('#total-raffles').text(stats.total);
        $('#processed-raffles').text(stats.processed);
        $('#unprocessed-raffles').text(stats.unprocessed);

        // Анимация обновления данных
        $('#total-raffles, #processed-raffles, #unprocessed-raffles').addClass('highlight');
        setTimeout(() => $('#total-raffles, #processed-raffles, #unprocessed-raffles').removeClass('highlight'), 2000);
    }

    // Обработка событий WebSocket
    socket.on('connect', function() {
        console.log('WebSocket подключен');
        $('#console-output').append('<pre>[Система] WebSocket соединение установлено</pre>');
        
        // Запрашиваем начальные данные
        fetchInitialData();
    });
    
    socket.on('system_stats_update', function(stats) {
        updateSystemStats(stats);
    });
    
    socket.on('raffle_stats_update', function(stats) {
        updateRaffleStats(stats);
    });
    
    socket.on('script_output', function(data) {
        const consoleOutput = $('#console-output');
        consoleOutput.append('<pre>' + data.data + '</pre>');
        consoleOutput.scrollTop(consoleOutput[0].scrollHeight);
    });
    
    socket.on('script_status', function(data) {
        console.log('Статус скрипта:', data.status);
    });

    // Получение начальных данных с сервера
    function fetchInitialData() {
        // Запрашиваем историю системных ресурсов
        fetch('/api/system_stats_history')
            .then(response => response.json())
            .then(data => {
                // Инициализация графика историческими данными
                if (data.length > 0) {
                    // Очищаем текущие данные
                    resourceChart.data.labels = [];
                    resourceChart.data.datasets.forEach(dataset => {
                        dataset.data = [];
                    });
                    
                    // Добавляем исторические данные
                    const historyLimit = Math.min(data.length, maxDataPoints);
                    for (let i = data.length - historyLimit; i < data.length; i++) {
                        const stats = data[i];
                        resourceChart.data.labels.push(stats.timestamp);
                        resourceChart.data.datasets[0].data.push(stats.cpu_percent);
                        resourceChart.data.datasets[1].data.push(stats.memory_percent);
                    }
                    
                    resourceChart.update();
                    
                    // Обновляем текущие значения
                    if (data.length > 0) {
                        updateSystemStats(data[data.length - 1]);
                    }
                }
            });
        
        // Запрашиваем статистику раздач
        fetch('/api/stats')
            .then(response => response.json())
            .then(data => {
                updateRaffleStats(data);
            });
    }
}); 