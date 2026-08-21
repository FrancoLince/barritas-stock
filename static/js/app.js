document.addEventListener('DOMContentLoaded', () => {
    const selectCliente = document.getElementById('cliente_id');
    const selectProducto = document.getElementById('producto_id');
    const inputCantidad = document.getElementById('cantidad_cajas');
    const inputPrecio = document.getElementById('precio_por_caja');
    const inputTotal = document.getElementById('total_calculado');
    const infoStock = document.getElementById('info-stock');

    function actualizarTotalesYPrecios() {
        const clienteId = selectCliente ? selectCliente.value : null;
        const productoId = selectProducto ? selectProducto.value : null;

        if (clienteId && productoId) {
            fetch(`/api/obtener-precio?cliente_id=${clienteId}&producto_id=${productoId}`)
                .then(response => response.json())
                .then(data => {
                    if (data.precio_sugerido !== undefined) {
                        // Solo actualiza el precio si no ha sido modificado manualmente por el usuario
                        if (!inputPrecio.dataset.userModified) {
                            inputPrecio.value = data.precio_sugerido;
                        }
                        if (infoStock) {
                            infoStock.textContent = `Stock disponible: ${data.stock_disponible} cajas`;
                        }
                        
                        // Establece límite máximo en el input de cantidad
                        if (inputCantidad) {
                            inputCantidad.max = data.stock_disponible;
                        }

                        calcularTotal();
                    }
                })
                .catch(err => console.error('Error al obtener precio:', err));
        }
    }

    function calcularTotal() {
        if (inputCantidad && inputPrecio && inputTotal) {
            const cantidad = parseFloat(inputCantidad.value) || 0;
            const precio = parseFloat(inputPrecio.value) || 0;
            const total = cantidad * precio;
            inputTotal.value = `$ ${total.toLocaleString('es-AR', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
        }
    }

    if (selectCliente && selectProducto) {
        selectCliente.addEventListener('change', () => {
            if (inputPrecio) delete inputPrecio.dataset.userModified;
            actualizarTotalesYPrecios();
        });

        selectProducto.addEventListener('change', () => {
            if (inputPrecio) delete inputPrecio.dataset.userModified;
            actualizarTotalesYPrecios();
        });
    }

    if (inputPrecio) {
        inputPrecio.addEventListener('input', () => {
            inputPrecio.dataset.userModified = 'true';
            calcularTotal();
        });
    }

    if (inputCantidad) {
        inputCantidad.addEventListener('input', calcularTotal);
    }
});