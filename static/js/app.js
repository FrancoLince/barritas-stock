let carrito = [];
let totalVentaCalculado = 0;

document.addEventListener('DOMContentLoaded', () => {
    // Referencias a elementos del DOM
    const selectCliente = document.getElementById('cliente_id');
    const selectProducto = document.getElementById('producto_id');
    const inputCantidad = document.getElementById('cantidad_cajas');
    const inputPrecio = document.getElementById('precio_por_caja');
    const inputTotal = document.getElementById('total_calculado');
    const infoStock = document.getElementById('info-stock');
    
    const formVenta = document.getElementById('formVenta');
    const btnAgregar = document.getElementById('btnAgregarItem');
    const observacionesSelect = document.getElementById('observaciones');
    const filtroEstadoTabla = document.getElementById('filtroEstadoTabla');

    // --- LÓGICA DE OBTENCIÓN DE PRECIO Y CÁLCULOS ---
    function actualizarTotalesYPrecios() {
        const clienteId = selectCliente ? selectCliente.value : null;
        const productoId = selectProducto ? selectProducto.value : null;

        if (clienteId && productoId) {
            fetch(`/api/obtener-precio?cliente_id=${clienteId}&producto_id=${productoId}`)
                .then(response => response.json())
                .then(data => {
                    if (data.precio_sugerido !== undefined) {
                        // Solo actualiza el precio si no ha sido modificado manualmente
                        if (inputPrecio && !inputPrecio.dataset.userModified) {
                            inputPrecio.value = data.precio_sugerido;
                        }
                        if (infoStock) {
                            infoStock.textContent = `Stock disponible: ${data.stock_disponible} cajas`;
                        }
                        if (inputCantidad && data.stock_disponible !== undefined) {
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

    // Event Listeners para Precios y Cantidades
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

    // --- LÓGICA DE VENTAS Y CARRITO MULTIPRODUCTO ---
    if (observacionesSelect) {
        observacionesSelect.addEventListener('change', togglePagoMixto);
    }

    if (btnAgregar) {
        btnAgregar.addEventListener('click', agregarItemAlCarrito);
    }

    if (formVenta) {
        formVenta.addEventListener('submit', validarFormularioVenta);
    }

    if (filtroEstadoTabla) {
        filtroEstadoTabla.addEventListener('change', calcularTotalesYFiltrar);
    }

    if (document.getElementById('tablaHistorialVentas')) {
        calcularTotalesYFiltrar();
    }
});

// Mostrar/Ocultar campos de pago mixto
function togglePagoMixto() {
    const obsSelect = document.getElementById('observaciones')?.value;
    const bloqueMixto = document.getElementById('bloquePagoMixto');
    if (bloqueMixto) {
        if (obsSelect === 'Mixto') {
            bloqueMixto.classList.remove('d-none');
        } else {
            bloqueMixto.classList.add('d-none');
        }
    }
}

// Agregar ítem al carrito de compras
function agregarItemAlCarrito() {
    const productoSelect = document.getElementById('producto_id');
    const cantidadInput = document.getElementById('cantidad_cajas');
    const precioInput = document.getElementById('precio_por_caja');

    if (!productoSelect || !cantidadInput || !precioInput) return;

    const productoId = productoSelect.value;
    const productoNombre = productoSelect.options[productoSelect.selectedIndex]?.text;
    const cantidad = parseInt(cantidadInput.value) || 0;
    const precio = parseFloat(precioInput.value) || 0;
    
    // Obtener limite maximo configurado o del atributo data-stock
    const maxStockAttr = productoSelect.options[productoSelect.selectedIndex]?.getAttribute('data-stock');
    const stockDisponible = cantidadInput.max ? parseInt(cantidadInput.max) : (maxStockAttr ? parseInt(maxStockAttr) : Infinity);

    if (!productoId || cantidad <= 0 || precio <= 0) {
        alert("Por favor completa los datos del producto correctamente.");
        return;
    }
    if (cantidad > stockDisponible) {
        alert(`Stock insuficiente. Solo hay ${stockDisponible} cajas disponibles.`);
        return;
    }

    const indexExistente = carrito.findIndex(item => item.producto_id === productoId);
    if (indexExistente !== -1) {
        if (carrito[indexExistente].cantidad + cantidad > stockDisponible) {
            alert(`Supera el stock disponible (${stockDisponible}).`);
            return;
        }
        carrito[indexExistente].cantidad += cantidad;
        carrito[indexExistente].precio = precio;
    } else {
        carrito.push({ producto_id: productoId, nombre: productoNombre, cantidad: cantidad, precio: precio });
    }

    renderizarCarrito();
    productoSelect.value = "";
    cantidadInput.value = 1;
    precioInput.value = "";
    delete precioInput.dataset.userModified;
    
    const infoStock = document.getElementById('info-stock');
    if (infoStock) infoStock.textContent = "";
}

// Renderizar tabla del carrito
function renderizarCarrito() {
    const tablaBody = document.querySelector('#tablaCarrito tbody');
    const totalVentaElem = document.getElementById('totalVenta');
    const carritoJsonInput = document.getElementById('carrito_json');

    if (!tablaBody) return;

    tablaBody.innerHTML = "";
    totalVentaCalculado = 0;

    carrito.forEach((item, index) => {
        const subtotal = item.cantidad * item.precio;
        totalVentaCalculado += subtotal;

        const tr = document.createElement('tr');
        tr.innerHTML = `
            <td>${item.nombre}</td>
            <td>${item.cantidad}</td>
            <td>$${item.precio.toFixed(2)}</td>
            <td>$${subtotal.toFixed(2)}</td>
            <td class="text-center"><button type="button" class="btn btn-sm btn-outline-danger" onclick="eliminarItem(${index})">❌</button></td>
        `;
        tablaBody.appendChild(tr);
    });

    if (totalVentaElem) totalVentaElem.textContent = `$${totalVentaCalculado.toFixed(2)}`;
    if (carritoJsonInput) carritoJsonInput.value = JSON.stringify(carrito);
}

function eliminarItem(index) {
    carrito.splice(index, 1);
    renderizarCarrito();
}

// Validar formulario de venta antes del submit
function validarFormularioVenta(e) {
    if (carrito.length === 0) {
        e.preventDefault();
        alert("Agrega al menos un producto al carrito.");
        return;
    }

    const obs = document.getElementById('observaciones')?.value;
    if (obs === 'Mixto') {
        const ef = parseFloat(document.getElementById('monto_efectivo')?.value) || 0;
        const tr = parseFloat(document.getElementById('monto_transferencia')?.value) || 0;
        
        if (Math.abs((ef + tr) - totalVentaCalculado) > 0.01) {
            e.preventDefault();
            alert(`La suma del efectivo ($${ef}) y transferencia ($${tr}) debe dar exactamente el total de la venta ($${totalVentaCalculado.toFixed(2)}).`);
        }
    }
}

// Calcular resúmenes y aplicar filtro en historial
function calcularTotalesYFiltrar() {
    const filtroElem = document.getElementById('filtroEstadoTabla');
    if (!filtroElem) return;

    const estadoSeleccionado = filtroElem.value;
    const filas = document.querySelectorAll('#tablaHistorialVentas tbody tr');

    let totalEfectivo = 0;
    let totalTransferencia = 0;
    let totalDebiendo = 0;
    let totalEnProceso = 0;

    filas.forEach(fila => {
        const estadoFila = fila.getAttribute('data-estado');
        const totalFila = parseFloat(fila.getAttribute('data-total')) || 0;
        const efFila = parseFloat(fila.getAttribute('data-efectivo')) || 0;
        const trFila = parseFloat(fila.getAttribute('data-transferencia')) || 0;

        if (!estadoFila) return;

        totalEfectivo += efFila;
        totalTransferencia += trFila;
        
        if (estadoFila === 'Debiendo') totalDebiendo += totalFila;
        if (estadoFila === 'En Proceso') totalEnProceso += totalFila;

        if (estadoSeleccionado === 'todos' || estadoFila === estadoSeleccionado) {
            fila.style.display = '';
        } else {
            fila.style.display = 'none';
        }
    });

    const elemEf = document.getElementById('montoEfectivo');
    const elemTr = document.getElementById('montoTransferencia');
    const elemDeb = document.getElementById('montoDebiendo');
    const elemProc = document.getElementById('montoEnProceso');

    if (elemEf) elemEf.textContent = `$${totalEfectivo.toLocaleString('es-AR', {minimumFractionDigits: 2, maximumFractionDigits: 2})}`;
    if (elemTr) elemTr.textContent = `$${totalTransferencia.toLocaleString('es-AR', {minimumFractionDigits: 2, maximumFractionDigits: 2})}`;
    if (elemDeb) elemDeb.textContent = `$${totalDebiendo.toLocaleString('es-AR', {minimumFractionDigits: 2, maximumFractionDigits: 2})}`;
    if (elemProc) elemProc.textContent = `$${totalEnProceso.toLocaleString('es-AR', {minimumFractionDigits: 2, maximumFractionDigits: 2})}`;
}
