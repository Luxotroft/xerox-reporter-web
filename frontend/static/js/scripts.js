document.addEventListener('DOMContentLoaded', function() {
    // Manejo del formulario
    const reportForm = document.getElementById('reportForm');
    if (reportForm) {
        reportForm.addEventListener('submit', function(e) {
            e.preventDefault();
            
            const formData = new FormData(reportForm);
            const data = Object.fromEntries(formData.entries());
            
            fetch('/save', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/x-www-form-urlencoded',
                },
                body: new URLSearchParams(data)
            })
            .then(response => response.json())
            .then(result => {
                if (result.success) {
                    alert(result.message);
                    reportForm.reset();
                } else {
                    alert(result.message);
                }
            })
            .catch(error => {
                console.error('Error:', error);
                alert('Error al guardar los datos');
            });
        });
    }
    
    // Botón limpiar
    const clearBtn = document.getElementById('clearBtn');
    if (clearBtn) {
        clearBtn.addEventListener('click', function() {
            document.getElementById('reportForm').reset();
        });
    }
    
    // Aquí puedes agregar más lógica JavaScript para otras páginas
});