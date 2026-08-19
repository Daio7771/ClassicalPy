/* ClassicalPy — cliente de la interfaz.
   Pide el informe en JSON a /api/analizar y lo pinta seccion a seccion.
   Todo el texto del informe viene del servidor; aqui solo se maqueta. */

'use strict';

const $ = (sel) => document.querySelector(sel);

const formulario = $('#formulario');
const entrada = $('#fuente');
const botonEnviar = $('#enviar');
const cajaEstado = $('#estado');
const seccionInforme = $('#informe');

/** Ultimo informe recibido, para los botones de copiar. */
let informeActual = null;

// ------------------------------------------------------------------ utilidades

/** Inserta texto como nodo de texto: nunca interpretamos HTML del informe. */
function elemento(tag, clase, texto) {
  const nodo = document.createElement(tag);
  if (clase) nodo.className = clase;
  if (texto !== undefined && texto !== null) nodo.textContent = texto;
  return nodo;
}

/* Separador de miles explícito: toLocaleString('es-ES') depende de datos de
   configuración regional que no todos los navegadores incluyen, y ahí devuelve
   el número sin agrupar. */
function miles(n) {
  return String(Math.round(Number(n) || 0)).replace(/\B(?=(\d{3})+(?!\d))/g, '.');
}

function mostrarEstado(mensaje, esError = false, cargando = false) {
  cajaEstado.textContent = mensaje;
  cajaEstado.classList.remove('oculto');
  cajaEstado.classList.toggle('error', esError);
  cajaEstado.classList.toggle('cargando', cargando);
}

function ocultarEstado() {
  cajaEstado.classList.add('oculto');
  cajaEstado.classList.remove('cargando', 'error');
}

// ------------------------------------------------------------------ secciones

function pintarPitch(informe) {
  $('#pitch').textContent = informe.pitch || '';

  const lista = $('#dominio');
  lista.replaceChildren();
  const dominio = informe.domain;
  if (!dominio) return;

  const filas = [
    ['Qué problema resuelve', dominio.problem],
    ['Quién es el usuario final', dominio.end_user],
    ['Confianza de la deducción', dominio.confidence],
  ];
  for (const [titulo, valor] of filas) {
    if (!valor) continue;
    lista.append(elemento('dt', null, titulo), elemento('dd', null, valor));
  }
}

function pintarStack(informe) {
  const caja = $('#arquitectura');
  caja.replaceChildren();

  const arq = informe.architecture;
  if (arq) {
    caja.append(elemento('span', 'patron', `${arq.pattern} · confianza ${arq.confidence}`));
    if (arq.rationale?.length) {
      const ul = elemento('ul', 'razones');
      arq.rationale.forEach((r) => ul.append(elemento('li', null, r)));
      caja.append(ul);
    }
  }

  const cuerpo = $('#tabla-stack tbody');
  cuerpo.replaceChildren();
  for (const tech of informe.stack || []) {
    const fila = document.createElement('tr');
    fila.append(elemento('td', 'tecnologia', tech.name));

    const celdaCat = document.createElement('td');
    celdaCat.append(elemento('span', 'categoria', tech.category));
    fila.append(celdaCat);

    const celdaVer = document.createElement('td');
    if (tech.version) celdaVer.append(elemento('code', 'version', tech.version));
    else celdaVer.textContent = '—';
    fila.append(celdaVer, elemento('td', null, tech.role));
    cuerpo.append(fila);
  }

  const stats = informe.stats || {};
  const metricas = $('#metricas');
  metricas.replaceChildren();
  const datos = [
    [miles(stats.total_files), 'Ficheros'],
    [miles(stats.total_lines), 'Líneas de código'],
    [`${((stats.total_bytes || 0) / 1048576).toFixed(1)} MB`, 'Tamaño'],
    [`${Math.round((stats.test_ratio || 0) * 100)} %`, 'Ficheros de test'],
  ];
  for (const [valor, nombre] of datos) {
    const bloque = elemento('div', 'metrica');
    bloque.append(elemento('span', 'valor', valor), elemento('span', 'nombre', nombre));
    metricas.append(bloque);
  }
}

function pintarFlujo(informe) {
  const lista = $('#flujo');
  lista.replaceChildren();
  for (const paso of informe.flow || []) {
    const li = document.createElement('li');
    li.append(
      elemento('span', 'actor', paso.actor),
      elemento('strong', 'titulo', paso.title),
      elemento('p', 'detalle', paso.detail),
    );
    if (paso.evidence) li.append(elemento('span', 'evidencia', `Evidencia: ${paso.evidence}`));
    lista.append(li);
  }
}

function pintarModulos(informe) {
  const lista = $('#modulos');
  lista.replaceChildren();
  for (const mod of informe.modules || []) {
    const li = document.createElement('li');
    // La profundidad de la ruta se refleja como sangría para leer la jerarquía.
    li.style.marginLeft = `${(mod.path.split('/').length - 1) * 1.1}rem`;

    const cabecera = document.createElement('div');
    cabecera.append(
      elemento('span', 'ruta', mod.path),
      elemento('span', 'rol', mod.role),
    );
    li.append(cabecera, elemento('p', 'proposito', mod.purpose));

    const partes = [`${mod.file_count} ficheros`];
    if (mod.languages?.length) partes.push(mod.languages.slice(0, 2).join(', '));
    if (mod.key_files?.length) partes.push(`p. ej. ${mod.key_files.slice(0, 2).join(', ')}`);
    li.append(elemento('span', 'meta', partes.join(' · ')));

    lista.append(li);
  }
}

const ETIQUETAS = {
  fortaleza: '✅ Bien resuelto',
  riesgo: '🚨 Riesgos',
  mejora: '⚠️ Áreas de mejora',
};

function pintarDiagnostico(informe) {
  const caja = $('#diagnostico');
  caja.replaceChildren();

  for (const tipo of ['fortaleza', 'riesgo', 'mejora']) {
    const grupo = (informe.findings || []).filter((f) => f.kind === tipo);
    if (!grupo.length) continue;

    caja.append(elemento('p', 'grupo-titulo', ETIQUETAS[tipo]));
    for (const hallazgo of grupo) {
      const art = elemento('article', `hallazgo ${tipo}`);
      art.append(elemento('h3', null, hallazgo.title), elemento('p', null, hallazgo.detail));
      if (hallazgo.impact) art.append(elemento('p', 'impacto', `Impacto: ${hallazgo.impact}`));
      if (hallazgo.evidence) art.append(elemento('span', 'evidencia', hallazgo.evidence));
      caja.append(art);
    }
  }
}

// ------------------------------------------------------------------ interacción

async function analizar(fuente) {
  botonEnviar.disabled = true;
  seccionInforme.classList.add('oculto');
  mostrarEstado('Analizando el proyecto… (clonar un repositorio grande puede tardar)', false, true);

  try {
    const respuesta = await fetch('/api/analizar', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ fuente, formato: 'json' }),
    });

    const cuerpo = await respuesta.json();
    if (!respuesta.ok) {
      throw new Error(cuerpo.detail || `El servidor respondió ${respuesta.status}.`);
    }

    informeActual = cuerpo;
    pintarPitch(cuerpo);
    pintarStack(cuerpo);
    pintarFlujo(cuerpo);
    pintarModulos(cuerpo);
    pintarDiagnostico(cuerpo);

    seccionInforme.classList.remove('oculto');
    if (cuerpo.warnings?.length) mostrarEstado(cuerpo.warnings.join(' · '));
    else ocultarEstado();
  } catch (error) {
    mostrarEstado(error.message || 'No se pudo completar el análisis.', true);
  } finally {
    botonEnviar.disabled = false;
  }
}

formulario.addEventListener('submit', (evento) => {
  evento.preventDefault();
  const fuente = entrada.value.trim();
  if (fuente) analizar(fuente);
});

document.querySelectorAll('[data-descarga]').forEach((boton) => {
  boton.addEventListener('click', async () => {
    if (!informeActual) return;
    const formato = boton.dataset.descarga;
    const original = boton.textContent;

    try {
      let texto;
      if (formato === 'json') {
        texto = JSON.stringify(informeActual, null, 2);
      } else {
        const respuesta = await fetch('/api/analizar', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ fuente: entrada.value.trim(), formato: 'markdown' }),
        });
        texto = await respuesta.text();
      }
      await navigator.clipboard.writeText(texto);
      boton.textContent = '¡Copiado!';
    } catch {
      boton.textContent = 'No se pudo copiar';
    }
    setTimeout(() => { boton.textContent = original; }, 1800);
  });
});

// Tema: se recuerda la elección entre visitas.
const botonTema = $('#tema');
const temaGuardado = localStorage.getItem('classicalpy-tema');
if (temaGuardado) document.documentElement.dataset.tema = temaGuardado;

botonTema.addEventListener('click', () => {
  const oscuroAhora = document.documentElement.dataset.tema === 'oscuro'
    || (!document.documentElement.dataset.tema
        && window.matchMedia('(prefers-color-scheme: dark)').matches);
  const siguiente = oscuroAhora ? 'claro' : 'oscuro';
  document.documentElement.dataset.tema = siguiente;
  localStorage.setItem('classicalpy-tema', siguiente);
});
