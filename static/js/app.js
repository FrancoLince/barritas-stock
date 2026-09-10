// ====================================================
// Estado global de los carritos
// ====================================================
let carrito = []; // Carrito de Ventas
let totalVentaCalculado = 0;

let carritoCompra = []; // Carrito de Compras
let totalCompraCalculado = 0;

// Función de utilidad para sanear texto (evitar XSS / HTML roto)
function escapeHTML(str) {
    if (!str) return '';
    return String(str)
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;')
        .replace(/'/g, '&#039;');
}

document.addEventListener('DOMContentLoaded', () => {
    // ----------------------------------------------------
    // 1. REFERENCIAS A ELEMENTOS DEL DOM
    // ----------------------------------------------------
    // Módulo Ventas
    const selectCliente = document.getElementById('cliente_id');
    const selectProductoVenta = document.getElementById('producto_id');
    const inputCantidadVenta = document.getElementById('cantidad_cajas');
    const inputPrecioVenta = document.getElementById('precio_por_caja');
    const infoStock = document.getElementById('info-stock');
    const formVenta = document.getElementById('formVenta');
    const btnAgregarVenta = document.getElementById('btnAgregarItem');
    const observacionesSelect = document.getElementById('observaciones');
    const tablaCarritoVenta = document.getElementById('tablaCarrito');

    // Módulo Compras
    const formCompra = document.getElementById('form-compra');
    const selectProductoCompra = document.getElementById('select_producto');
    const inputCantidadCompra = document.getElementById('input_cantidad');
    const inputCostoCompra = document.getElementById('input_costo');
    const btnAgregarCompra = document.getElementById('btn-agregar-item');
    const medioPagoCompraSelect = document.getElementById('medio_pago');
    const tablaCarritoCompra = document.getElementById('tabla-carrito');

    // UI & Tablas Generales
    const filtroEstadoTabla = document.getElementById('filtroEstadoTabla');
    const sidebar = document.getElementById('sidebar');
    const overlay = document.getElementById('sidebarOverlay');
    const mobileMenuBtn = document.getElementById('mobileMenuBtn');

    // ----------------------------------------------------
    // 2. LÓGICA DE PRECIOS Y STOCK DESDE API (VENTAS)
    // ----------------------------------------------------
    function actualizarTotalesYPrecios() {
        const clienteId = selectCliente?.value;
        const productoId = selectProductoVenta?.value;

        if (clienteId && productoId) {
            fetch(`/api/obtener-precio?cliente_id=${encodeURIComponent(clienteId)}&producto_id=${encodeURIComponent(productoId)}`)
                .then(response => {
                    if (!response.ok) throw new Error('Error en la respuesta de la API');
                    return response.json();
                })
                .then(data => {
                    if (data.precio_sugerido !== undefined) {
                        if (inputPrecioVenta && !inputPrecioVenta.dataset.userModified) {
                            inputPrecioVenta.value = parseFloat(data.precio_sugerido).toFixed(2);
                        }
                        if (infoStock) {
                            infoStock.textContent = `Stock disponible: ${data.stock_disponible} cajas`;
                        }
                        if (inputCantidadVenta && data.stock_disponible !== undefined) {
                            inputCantidadVenta.max = data.stock_disponible;
                            if (parseInt(inputCantidadVenta.value) > data.stock_disponible) {
                                inputCantidadVenta.value = data.stock_disponible > 0 ? 1 : 0;
                            }
                        }
                    }
                })
                .catch(err => console.error('Error al obtener precio:', err));
        }
    }

    // Auto-completar costo sugerido en Compras
    if (selectProductoCompra) {
        selectProductoCompra.addEventListener('change', () => {
            const option = selectProductoCompra.options[selectProductoCompra.selectedIndex];
            if (option && option.value) {
                const costo = option.getAttribute('data-costo');
                if (costo && inputCostoCompra) {
                    inputCostoCompra.value = parseFloat(costo).toFixed(2);
                }
            }
        });
    }

    // ----------------------------------------------------
    // 3. LISTENERS PARA EVENTOS DE FORMULARIO
    // ----------------------------------------------------
    // Ventas
    if (selectCliente && selectProductoVenta) {
        selectCliente.addEventListener('change', () => {
            if (inputPrecioVenta) delete inputPrecioVenta.dataset.userModified;
            actualizarTotalesYPrecios();
        });

        selectProductoVenta.addEventListener('change', () => {
            if (inputPrecioVenta) delete inputPrecioVenta.dataset.userModified;
            actualizarTotalesYPrecios();
        });
    }

    if (inputPrecioVenta) {
        inputPrecioVenta.addEventListener('input', () => {
            inputPrecioVenta.dataset.userModified = 'true';
        });
    }

    if (observacionesSelect) {
        observacionesSelect.addEventListener('change', togglePagoMixto);
    }

    if (btnAgregarVenta) {
        btnAgregarVenta.addEventListener('click', agregarItemAlCarritoVenta);
    }

    if (formVenta) {
        formVenta.addEventListener('submit', validarFormularioVenta);
    }

    // Compras
    if (medioPagoCompraSelect) {
        medioPagoCompraSelect.addEventListener('change', togglePagoMixtoCompra);
    }

    if (btnAgregarCompra) {
        btnAgregarCompra.addEventListener('click', agregarItemAlCarritoCompra);
    }

    if (formCompra) {
        formCompra.addEventListener('submit', validarFormularioCompra);
    }

    // Filtros & Historiales
    if (filtroEstadoTabla) {
        filtroEstadoTabla.addEventListener('change', calcularTotalesYFiltrar);
    }

    if (document.getElementById('tablaHistorialVentas')) {
        calcularTotalesYFiltrar();
    }

    // Delegación de eventos para eliminar ítems en carrito de Ventas
    if (tablaCarritoVenta) {
        tablaCarritoVenta.addEventListener('click', (e) => {
            const btnEliminar = e.target.closest('.btn-eliminar-item');
            if (btnEliminar) {
                const index = parseInt(btnEliminar.getAttribute('data-index'), 10);
                eliminarItemCarritoVenta(index);
            }
        });
    }

    // Delegación de eventos para eliminar ítems en carrito de Compras
    if (tablaCarritoCompra) {
        tablaCarritoCompra.addEventListener('click', (e) => {
            const btnEliminar = e.target.closest('.btn-eliminar-compra-item');
            if (btnEliminar) {
                const index = parseInt(btnEliminar.getAttribute('data-index'), 10);
                eliminarItemCarritoCompra(index);
            }
        });
    }

    // ----------------------------------------------------
    // 4. INTERFAZ UI / SIDEBAR / ALERTAS
    // ----------------------------------------------------
    const toggleSidebar = () => {
        if (sidebar) sidebar.classList.toggle('sidebar-open');
        if (overlay) overlay.classList.toggle('active');
    };

    if (mobileMenuBtn) mobileMenuBtn.addEventListener('click', toggleSidebar);
    if (overlay) overlay.addEventListener('click', toggleSidebar);

    // Cierre de alertas
    document.querySelectorAll('.custom-alert .btn-close-custom').forEach(button => {
        button.addEventListener('click', (e) => {
            e.target.closest('.custom-alert')?.remove();
        });
    });

    // Confirmación global de formularios con atributo data-confirm
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
// 5. FUNCIONES DE VENTAS
// ----------------------------------------------------

function togglePagoMixto() {
    const obsSelect = document.getElementById('observaciones')?.value;
    const bloqueMixto = document.getElementById('bloquePagoMixto');
    if (bloqueMixto) {
        bloqueMixto.classList.toggle('d-none', obsSelect !== 'Mixto');
    }
}

function agregarItemAlCarritoVenta() {
    const productoSelect = document.getElementById('producto_id');
    const cantidadInput = document.getElementById('cantidad_cajas');
    const precioInput = document.getElementById('precio_por_caja');

    if (!productoSelect || !cantidadInput || !precioInput) return;

    const productoId = productoSelect.value;
    const productoNombre = productoSelect.options[productoSelect.selectedIndex]?.text;
    const cantidad = parseInt(cantidadInput.value, 10) || 0;
    const precio = parseFloat(precioInput.value) || 0;

    const maxStockAttr = productoSelect.options[productoSelect.selectedIndex]?.getAttribute('data-stock');
    const stockDisponible = cantidadInput.max !== "" ? parseInt(cantidadInput.max, 10) : (maxStockAttr ? parseInt(maxStockAttr, 10) : Infinity);

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

    renderizarCarritoVenta();
    productoSelect.value = "";
    cantidadInput.value = 1;
    precioInput.value = "";
    delete precioInput.dataset.userModified;

    const infoStock = document.getElementById('info-stock');
    if (infoStock) infoStock.textContent = "";
}

function renderizarCarritoVenta() {
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
            <td>${escapeHTML(item.nombre)}</td>
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

function eliminarItemCarritoVenta(index) {
    carrito.splice(index, 1);
    renderizarCarritoVenta();
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
        const suma = Math.round((ef + tr) * 100) / 100;
        const total = Math.round(totalVentaCalculado * 100) / 100;

        if (Math.abs(suma - total) > 0.01) {
            e.preventDefault();
            alert(`La suma del efectivo ($${ef.toFixed(2)}) y transferencia ($${tr.toFixed(2)}) debe ser exactamente $${total.toFixed(2)}.`);
        }
    }
}

// ----------------------------------------------------
// 6. FUNCIONES DE COMPRAS
// ----------------------------------------------------

function togglePagoMixtoCompra() {
    const medioPago = document.getElementById('medio_pago')?.value;
    const divMixto = document.getElementById('div_pago_mixto_compra');
    const inputEf = document.getElementById('monto_efectivo_compra') || document.getElementById('monto_efectivo');
    const inputTr = document.getElementById('monto_transferencia_compra') || document.getElementById('monto_transferencia');

    if (divMixto && inputEf && inputTr) {
        if (medioPago === 'Mixto') {
            divMixto.style.display = 'block';
            divMixto.classList.remove('d-none', 'hidden');
            inputEf.required = true;
            inputTr.required = true;
        } else {
            divMixto.style.display = 'none';
            divMixto.classList.add('d-none');
            inputEf.required = false;
            inputTr.required = false;
            inputEf.value = '0';
            inputTr.value = '0';
        }
    }
}

function agregarItemAlCarritoCompra() {
    const selectProducto = document.getElementById('select_producto');
    const inputCantidad = document.getElementById('input_cantidad');
    const inputCosto = document.getElementById('input_costo');

    if (!selectProducto || !inputCantidad || !inputCosto) return;

    const productoId = selectProducto.value;
    const option = selectProducto.options[selectProducto.selectedIndex];
    const productoNombre = option ? (option.getAttribute('data-nombre') || option.text) : '';
    const cantidad = parseInt(inputCantidad.value, 10) || 0;
    const costo = parseFloat(inputCosto.value) || 0;

    if (!productoId) {
        alert("Por favor, selecciona un producto.");
        return;
    }
    if (cantidad <= 0) {
        alert("La cantidad debe ser mayor a 0.");
        return;
    }
    if (costo <= 0) {
        alert("El costo por caja debe ser mayor a 0.");
        return;
    }

    const indexExistente = carritoCompra.findIndex(item => item.producto_id === productoId);
    if (indexExistente !== -1) {
        carritoCompra[indexExistente].cantidad += cantidad;
        carritoCompra[indexExistente].costo_unitario = costo;
        carritoCompra[indexExistente].subtotal = carritoCompra[indexExistente].cantidad * costo;
    } else {
        carritoCompra.push({
            producto_id: productoId,
            nombre: productoNombre,
            cantidad: cantidad,
            costo_unitario: costo,
            subtotal: cantidad * costo
        });
    }

    renderizarCarritoCompra();
    selectProducto.value = "";
    inputCantidad.value = "1";
    inputCosto.value = "";
}

function renderizarCarritoCompra() {
    const bodyCarrito = document.getElementById('body-carrito');
    const totalCompraElem = document.getElementById('total-compra');
    const carritoDataInput = document.getElementById('carrito_data');

    if (!bodyCarrito) return;

    bodyCarrito.innerHTML = "";
    totalCompraCalculado = 0;

    if (carritoCompra.length === 0) {
        bodyCarrito.innerHTML = '<tr id="tr-vacio"><td colspan="5" class="text-center text-muted">No has agregado productos al detalle.</td></tr>';
        if (totalCompraElem) totalCompraElem.textContent = '$0.00';
        if (carritoDataInput) carritoDataInput.value = '';
        return;
    }

    carritoCompra.forEach((item, index) => {
        totalCompraCalculado += item.subtotal;

        const tr = document.createElement('tr');
        tr.innerHTML = `
            <td>${escapeHTML(item.nombre)}</td>
            <td>${item.cantidad}</td>
            <td>$${item.costo_unitario.toFixed(2)}</td>
            <td><strong>$${item.subtotal.toFixed(2)}</strong></td>
            <td class="text-center">
                <button type="button" class="btn btn-sm btn-outline-danger btn-eliminar-compra-item" data-index="${index}">🗑️</button>
            </td>
        `;
        bodyCarrito.appendChild(tr);
    });

    if (totalCompraElem) totalCompraElem.textContent = `$${totalCompraCalculado.toFixed(2)}`;
    if (carritoDataInput) carritoDataInput.value = JSON.stringify(carritoCompra);
}

function eliminarItemCarritoCompra(index) {
    carritoCompra.splice(index, 1);
    renderizarCarritoCompra();
}

function validarFormularioCompra(e) {
    if (carritoCompra.length === 0) {
        e.preventDefault();
        alert("Debes agregar al menos un producto al detalle antes de registrar la compra.");
        return;
    }

    const medioPago = document.getElementById('medio_pago')?.value;
    if (medioPago === 'Mixto') {
        const inputEf = document.getElementById('monto_efectivo_compra') || document.getElementById('monto_efectivo');
        const inputTr = document.getElementById('monto_transferencia_compra') || document.getElementById('monto_transferencia');
        
        const ef = parseFloat(inputEf?.value) || 0;
        const tr = parseFloat(inputTr?.value) || 0;
        const suma = Math.round((ef + tr) * 100) / 100;
        const total = Math.round(totalCompraCalculado * 100) / 100;

        if (Math.abs(suma - total) > 0.01) {
            e.preventDefault();
            alert(`La suma del efectivo ($${ef.toFixed(2)}) y transferencia ($${tr.toFixed(2)}) debe ser exactamente $${total.toFixed(2)}.`);
        }
    }
}

// ----------------------------------------------------
// 7. OTROS FILTROS DE TABLAS
// ----------------------------------------------------

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
