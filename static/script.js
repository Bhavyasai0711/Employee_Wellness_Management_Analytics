document.addEventListener("DOMContentLoaded", () => {
    document.querySelectorAll(".toast").forEach((toast) => {
        bootstrap.Toast.getOrCreateInstance(toast, { delay: 4500 }).show();
    });

    document.querySelectorAll(".toggle-password").forEach((button) => {
        button.addEventListener("click", () => {
            const input = button.closest(".input-group").querySelector(".password-input");
            const icon = button.querySelector("i");
            input.type = input.type === "password" ? "text" : "password";
            icon.classList.toggle("fa-eye");
            icon.classList.toggle("fa-eye-slash");
        });
    });

    document.querySelectorAll(".password-rules-form").forEach((form) => {
        const password = form.querySelector(".strength-password");
        const confirm = form.querySelector(".confirm-password");
        const progress = form.querySelector(".progress-bar");
        const rules = {
            length: (value) => value.length >= 8,
            upper: (value) => /[A-Z]/.test(value),
            lower: (value) => /[a-z]/.test(value),
            number: (value) => /\d/.test(value),
            special: (value) => /[^A-Za-z0-9]/.test(value),
            match: (value) => value.length > 0 && value === confirm.value,
        };

        const update = () => {
            const value = password.value;
            let score = 0;
            Object.entries(rules).forEach(([name, test]) => {
                const item = form.querySelector(`[data-rule="${name}"]`);
                const valid = test(value);
                if (valid) score += 1;
                item.classList.toggle("valid", valid);
                item.querySelector("i").className = valid ? "fa-solid fa-circle-check" : "fa-regular fa-circle";
            });
            const percent = Math.round((score / Object.keys(rules).length) * 100);
            progress.style.width = `${percent}%`;
            progress.className = `progress-bar ${percent < 50 ? "bg-danger" : percent < 84 ? "bg-warning" : "bg-success"}`;
        };

        password.addEventListener("input", update);
        confirm.addEventListener("input", update);
        update();
    });

    if (window.healthCharts && window.Chart) {
        const chartColors = ["#0b5cab", "#16a3b8", "#168a55", "#f59e0b", "#ef4444", "#64748b"];
        const makeChart = (id, type, title, payload) => {
            const canvas = document.getElementById(id);
            if (!canvas || !payload) return;
            new Chart(canvas, {
                type,
                data: {
                    labels: payload.labels,
                    datasets: [{
                        label: title,
                        data: payload.values,
                        backgroundColor: chartColors,
                        borderColor: "#ffffff",
                        borderWidth: type === "line" ? 2 : 1,
                    }],
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {
                        legend: { display: type !== "bar" && type !== "line" },
                        title: { display: true, text: title },
                    },
                    scales: type === "bar" || type === "line" ? { y: { beginAtZero: true } } : {},
                },
            });
        };

        makeChart("bmiChart", "doughnut", "BMI Distribution", window.healthCharts.bmi);
        makeChart("ageChart", "bar", "Age Distribution", window.healthCharts.age);
        makeChart("stressChart", "doughnut", "Stress Level", window.healthCharts.stress);
        makeChart("sleepChart", "bar", "Sleep Analysis", window.healthCharts.sleep);
        makeChart("exerciseChart", "pie", "Exercise Frequency", window.healthCharts.exercise);
        makeChart("attendanceChart", "line", "Attendance", window.healthCharts.attendance);
    }
});
