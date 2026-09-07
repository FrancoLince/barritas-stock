// Variables de estado global del carrito
let carrito = [];
let totalVentaCalculado = 0;

document.addEventListener('DOMContentLoaded', () => {
    // ----------------------------------------------------
    // 1. REFERENCIAS A ELEMENTOS DEL DOM
    // ----------------------------------------------------
    const selectCliente = document.getElementById('cliente_id');
    const selectProducto = document.getElementById('producto_id');
    const inputCantidad = document.getElementById('cantidad_cajas');
    const inputPrecio = document.getElementById('precio_por_caja');
    const infoStock = document.getElementById('info-stock');
    
    const formVenta = document.getElementById('formVenta');
    const btnAgregar = document.getElementById('btnAgregarItem');
    const observacionesSelect = document.getElementById('observaciones');
    const filtroEstadoTabla = document.getElementById('filtroEstadoTabla');
    
    const sidebar = document.getElementById('sidebar');
    const overlay = document.getElementById('sidebarOverlay');
    const mobileMenuBtn = document.getElementById('mobileMenuBtn');
    const tablaCarrito = document.getElementById('tablaCarrito');

    // ----------------------------------------------------
    // 2. LÓGICA DE PRECIOS Y STOCK DESDE API
    // ----------------------------------------------------
    function actualizarTotalesYPrecios() {
        const clienteId = selectCliente?.value;
        const productoId = selectProducto?.value;

        if (clienteId && productoId) {
            fetch(`/api/obtener-precio?cliente_id=${clienteId}&producto_id=${productoId}`)
                .then(response => response.json())
                .then(data => {
                    if (data.precio_sugerido !== undefined) {
                        if (inputPrecio && !inputPrecio.dataset.userModified) {
                            inputPrecio.value = data.precio_sugerido;
                        }
                        if (infoStock) {
                            infoStock.textContent = `Stock disponible: ${data.stock_disponible} cajas`;
                        }
                        if (inputCantidad && data.stock_disponible !== undefined) {
                            inputCantidad.max = data.stock_disponible;
                        }
                    }
                })
                .catch(err => console.error('Error al obtener precio:', err));
        }
    }

    // ----------------------------------------------------
    // 3. LISTENERS PARA EVENTOS DE FORMULARIO
    // ----------------------------------------------------
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
        });
    }

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

    if (tablaCarrito) {
        tablaCarrito.addEventListener('click', (e) => {
            const btnEliminar = e.target.closest('.btn-eliminar-item');
            if (btnEliminar) {
                const index = parseInt(btnEliminar.getAttribute('data-index'));
                eliminarItemCarrito(index);
            }
        });
    }

    // ----------------------------------------------------
    // 4. INTERFAZ UI / SIDEBAR MÓVIL / ALERTAS
    // ----------------------------------------------------
    const toggleSidebar = () => {
        if (sidebar) {
            sidebar.classList.toggle('sidebar-open');
            sidebar.classList.toggle('active');
        }
        if (overlay) {
            overlay.classList.toggle('active');
            overlay.classList.toggle('show');
        }
    };

    if (mobileMenuBtn) mobileMenuBtn.addEventListener('click', toggleSidebar);
    if (overlay) overlay.addEventListener('click', toggleSidebar);

    // Cerrar sidebar al hacer clic en cualquier opción del menú en celular
    document.querySelectorAll('.sidebar-nav a').forEach(link => {
        link.addEventListener('click', () => {
            if (window.innerWidth <= 768 && sidebar?.classList.contains('sidebar-open')) {
                toggleSidebar();
            }
        });
    });

    // Cierre de alertas
    document.querySelectorAll('.custom-alert .btn-close-custom').forEach(button => {
        button.addEventListener('click', (e) => {
            e.target.closest('.custom-alert')?.remove();
        });
    });

    // Confirmación global de formularios con data-confirm
    document.addEventListener('submit', (e) => {
        const form = e.target;
        if (form.hasAttribute('data-confirm')) {
            const message = form.getAttribute('data-confirm') || '¿Confirmas realizar esta acción?';
            if (!confirm(message)) {
                e.preventDefault();
            }
        }
    });
});

// ----------------------------------------------------
// 5. FUNCIONES AUXILIARES DEL CARRITO Y VENTAS
// ----------------------------------------------------

function togglePagoMixto() {
    const obsSelect = document.getElementById('observaciones')?.value;
    const bloqueMixto = document.getElementById('bloquePagoMixto');
    if (bloqueMixto) {
        bloqueMixto.classList.toggle('d-none', obsSelect !== 'Mixto');
    }
}

function agregarItemAlCarrito() {
    const productoSelect = document.getElementById('producto_id');
    const cantidadInput = document.getElementById('cantidad_cajas');
    const precioInput = document.getElementById('precio_por_caja');

    if (!productoSelect || !cantidadInput || !precioInput) return;

    const productoId = productoSelect.value;
    const productoNombre = productoSelect.options[productoSelect.selectedIndex]?.text;
    const cantidad = parseInt(cantidadInput.value) || 0;
    const precio = parseFloat(precioInput.value) || 0;
    
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
            <td class="text-center">
                <button type="button" class="btn btn-sm btn-outline-danger btn-eliminar-item" data-index="${index}">❌</button>
            </td>
        `;
        tablaBody.appendChild(tr);
    });

    if (totalVentaElem) totalVentaElem.textContent = `$${totalVentaCalculado.toFixed(2)}`;
    if (carritoJsonInput) carritoJsonInput.value = JSON.stringify(carrito);
}

function eliminarItemCarrito(index) {
    carrito.splice(index, 1);
    renderizarCarrito();
}

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

        fila.style.display = (estadoSeleccionado === 'todos' || estadoFila === estadoSeleccionado) ? '' : 'none';
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
