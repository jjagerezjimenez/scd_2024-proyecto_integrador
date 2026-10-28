# Enlace punto a punto half-duplex con 4-QAM en GNU Radio

Proyecto de *Sistemas de Comunicaciones Digitales* (FACET – UNT). Radio definida por software simulada en
GNU Radio, armada **solo con bloques estándar** (ningún bloque propio): cualquier persona puede abrir los `.grc` y
ejecutarlos sin instalar nada extra.

| Requisito | Cómo se cumple | Dónde |
|---|---|---|
| Punto a punto **half-duplex** | Dos nodos (A y B) comparten un único canal y se turnan por división en el tiempo (TDD): `Stream Mux` arma los turnos y `Stream Demux` es el conmutador de recepción. Ningún nodo se escucha a sí mismo. | `grc_estandar/halfduplex_4qam.grc` |
| Trama simple con **preámbulo y longitud** | Encabezado estándar de GNU Radio: `preámbulo (64 bits) ‖ longitud ‖ longitud ‖ payload ‖ CRC-32` | `Protocol Formatter` |
| **CRC-32** | `Stream CRC32`: lo agrega el transmisor y lo verifica el receptor, que descarta las tramas erróneas. | todos los `.grc` |
| **4-QAM** | `Constellation Modulator`: constelación Gray, codificación diferencial, filtro RRC (roll-off 0,35, 4 muestras/símbolo). | todos los `.grc` |
| **BER teórico** vs SNR | `Pb = Q(√(2·Eb/N0))`; con codificación diferencial `2p(1−p)`; PER y BER con error de fase. | `ber_teorico.py`, `INFORME.md` §2 |
| **Simulación** en GNU Radio | Tres flowgraphs (ver abajo). | `grc_estandar/` |
| **BER medido** en distintas condiciones de canal y comparación con la teoría | Barrido automático de Eb/N0 × 4 condiciones de canal, con intervalos de confianza. | `run_ber_sweep.py`, `resultados/`, `INFORME.md` §6 |
| **Prueba de laboratorio** transmitiendo archivos con **HackRF** | El mismo sistema (tramas, 4-QAM, receptor) con `Soapy HackRF Sink/Source`: paquetes numerados, varias pasadas y verificación SHA-256 del archivo recibido. Probado sin hardware con un canal de laboratorio simulado. | `grc_hackrf/`, `LABORATORIO_HACKRF.md` |

## Contenido

```
INFORME.md / INFORME.pdf      informe técnico: teoría, diseño, resultados y análisis
grc_estandar/
  enlace_4qam_tramas.grc      enlace en un solo sentido con un gráfico por etapa (para entender cada bloque)
  halfduplex_4qam.grc         SISTEMA COMPLETO: dos nodos half-duplex (TDD) con interfaz
  halfduplex_4qam_ber.grc     el mismo half-duplex sin interfaz, con parámetros, para medir BER
grc_hackrf/                   PRUEBA DE LABORATORIO con HackRF (ver LABORATORIO_HACKRF.md)
  hackrf_tx_archivo.grc       transmite un archivo en paquetes numerados por un HackRF
  hackrf_rx_archivo.grc       recibe con otro HackRF y guarda los paquetes con CRC correcto
  archivo_a_enviar.txt        archivo de ejemplo
  capturas_simuladas/         cómo se ven las interfaces cuando funciona (HackRF simulado)
hackrf_simulada/              ENSAYO DEL LABORATORIO EN UNA SOLA PC, sin placas (ver hackrf_simulada/LEEME.md)
  emulador_hackrf.py          hace de las dos HackRF One y del aire; se deja corriendo en un radioconda Prompt
  hackrf_*_archivo_sim.grc    los .grc del laboratorio con bloques de red en lugar del bloque Soapy HackRF
  generar_grc_simulados.py    vuelve a armar los _sim.grc si cambian los de grc_hackrf/
  prueba_completa.py          prueba de punta a punta con el emulador (9 casos, ~40 s)
LABORATORIO_HACKRF.md / .pdf  guía de la prueba: seguridad, procedimiento, mediciones y problemas comunes
GUIA_PASO_A_PASO.md / .pdf    guía muy simple: ensayo con la HackRF simulada y después la prueba con las placas
reconstruir_archivo.py        arma el archivo recibido, cuenta paquetes perdidos y verifica la huella SHA-256
run_ber_sweep.py              barrido de BER vs Eb/N0 (usa halfduplex_4qam_ber.grc) -> resultados/
ber_teorico.py                BER/SER/PER teóricos + verificación Monte Carlo (no necesita GNU Radio)
resultados/                   CSV, gráficos, tabla de pérdidas y capturas de las interfaces
tests/test_flowgraphs.py      pruebas con GNU Radio real
tests/test_hackrf.py          pruebas de grc_hackrf/ sin HackRF (canal de laboratorio simulado)
tools/informe_pdf.py          genera INFORME.pdf (o el PDF de otro .md, como la guía del laboratorio)
```

## Requisitos

* **GNU Radio 3.10** con Python 3. Probado con GNU Radio 3.10.12 y Python 3.11 (RadioConda, Windows).
* Para los scripts: `numpy`, `scipy` y `matplotlib` (vienen con RadioConda).

**En Windows (RadioConda):** usá el *radioconda Prompt* (o `D:\Programas\RadioConda\python.exe`) y `python` en
lugar de `python3`.

## Uso

### Con GNU Radio Companion

```bash
gnuradio-companion grc_estandar/halfduplex_4qam.grc       # F6 para ejecutar
gnuradio-companion grc_estandar/enlace_4qam_tramas.grc
```

* **Controles:** Eb/N0, fase del canal, CFO / desvío entre osciladores de A y B, y ancho de banda de los lazos de Costas
  y de sincronismo de símbolo. Arriba se ven el BER teórico y el medido (acumulado; en el enlace simple también el del
  último millón de bits).
* `halfduplex_4qam.grc` tiene 3 pestañas: **canal compartido** (turnos de A y B, espectro, señal de cada transmisor),
  **nodo A recibe** y **nodo B recibe** (ojo, constelación antes y después de Costas, frecuencia estimada, bits recibidos
  vs transmitidos, payload detectado, log₁₀(BER) vs teoría).
* `enlace_4qam_tramas.grc` tiene 3 pestañas: **transmisor y canal**, **receptor** (filtro adaptado, ojo, sincronismo,
  constelaciones, histograma) y **tramas, bits y BER**.
* Los mensajes recibidos con CRC correcto se guardan (uno de cada 100) en `mensajes_recibidos*.txt`, en la carpeta
  `grc_estandar/`.
* **Cerrá la ventana con la X.** Si se detiene con el botón rojo de GRC, Windows termina el proceso y GRC muestra
  `return code 1` (no es un error del flowgraph).
* A Eb/N0 alto hay pocos errores: el BER mostrado tarda en estabilizarse (a 10 dB, minutos). Para medir curvas usá el
  barrido.

### Barrido de BER

```bash
python run_ber_sweep.py                                  # completo: 4 condiciones x 0..10 dB, ~30 s
python run_ber_sweep.py --quick                          # más rápido y más ruidoso
python run_ber_sweep.py --scenarios awgn --ebn0 0:10:1   # solo AWGN
python run_ber_sweep.py --out otra_carpeta               # sin pisar resultados/
python run_ber_sweep.py --plot-only                      # rehacer gráficos desde el CSV
```

El script compila `grc_estandar/halfduplex_4qam_ber.grc` con `grcc` (en `build/`) y lo ejecuta una vez por punto: el
`.grc` es la única descripción del enlace. Genera `resultados/resultados_ber.csv`, los gráficos de BER y PER y
`resultados/resumen_perdidas.md`. Con la misma semilla da siempre los mismos números.

El flowgraph de medición también se puede compilar y correr solo (termina en menos de un segundo con los valores por
defecto; no imprime resultados: los contadores de errores y de tramas los lee `run_ber_sweep.py`):

```bash
grcc -o build grc_estandar/halfduplex_4qam_ber.grc
python build/halfduplex_4qam_ber.py --help
```

### Prueba de laboratorio con HackRF

Para empezar, la guía más simple: `GUIA_PASO_A_PASO.md` (o `.pdf`). Primero se ensaya en la PC con la HackRF
simulada y después se repiten los mismos pasos con las placas. Guía completa (seguridad, procedimiento, tabla de
mediciones y problemas comunes): `LABORATORIO_HACKRF.md` (o `LABORATORIO_HACKRF.pdf` para imprimir). En resumen:

```bash
hackrf_info                                               # se tienen que ver los dos HackRF
gnuradio-companion grc_hackrf/hackrf_rx_archivo.grc       # 1) receptor primero (F6)
gnuradio-companion grc_hackrf/hackrf_tx_archivo.grc       # 2) transmisor: parámetros 'archivo' y 'repeticiones'
python reconstruir_archivo.py                             # 3) arma grc_hackrf/recibido_<nombre> y verifica SHA-256
```

* Frecuencia por defecto 915 MHz (banda ISM): usar la que autorice la cátedra, con la potencia mínima. **Nunca unir
  TX y RX con cable sin un atenuador de 30 dB o más.**
* El HackRF es half-duplex: en cada prueba un nodo transmite y el otro recibe; después se invierten los papeles.
* El archivo se envía en pasadas: [relleno | paquetes numerados | paquete con nombre, tamaño y huella SHA-256].
  Un paquete perdido en una pasada se recupera en otra.
* Antes del laboratorio: `python tests/test_hackrf.py` prueba los dos `.grc` sin HackRF, con desvíos de hasta
  ±40 kHz entre osciladores, relojes distintos, ruido de fase y portadora residual.
* Ensayo completo en una sola PC: `hackrf_simulada/LEEME.md`. Se deja corriendo
  `python hackrf_simulada/emulador_hackrf.py`, se abren en GRC `hackrf_simulada/hackrf_rx_archivo_sim.grc` y
  `hackrf_tx_archivo_sim.grc` (F6) y al final se corre `python reconstruir_archivo.py hackrf_simulada/paquetes_recibidos.bin`.

### Teoría, pruebas e informe

```bash
python ber_teorico.py --montecarlo      # tabla, gráfico resultados/ber_teorico.png y verificación Monte Carlo
python tests/test_flowgraphs.py         # 9 pruebas con GNU Radio real (~30 s)
python tests/test_hackrf.py             # 7 pruebas de grc_hackrf/ con un HackRF simulado (< 1 min)
python hackrf_simulada/prueba_completa.py  # 9 casos de punta a punta con el emulador de HackRF (~40 s)
python tools/informe_pdf.py             # INFORME.md -> INFORME.pdf (usa Microsoft Edge, sin abrir ventanas)
python tools/informe_pdf.py LABORATORIO_HACKRF.md         # -> LABORATORIO_HACKRF.pdf
```

## Resultados (resumen)

| Condición de canal | Pérdida respecto de la teoría (2–10 dB) | Medido / teórico |
|---|---:|---:|
| AWGN ideal | +0,08 dB | 1,04 |
| Fase 20° sin corregir | +0,02 dB | 1,01 |
| Fase 20° con lazo de Costas | +0,08 dB | 1,04 |
| Fase 20° + desvío de 200 Hz con lazo de Costas | +0,08 dB | 1,04 |

De 206.473 tramas aceptadas por el CRC, ninguna tenía contenido distinto del transmitido. Detalle en `INFORME.md` §6.

## Solución de problemas

* `>>> Warning: This flow graph may not have flow control` al compilar `halfduplex_4qam_ber.grc`: es intencional (sin
  `Throttle` corre a máxima velocidad para medir).
* Al cerrar una interfaz, a veces aparece `RuntimeError: wrapped C/C++ object ... has been deleted`: es inofensivo; viene
  del bloque estándar `Function Probe`, cuyo hilo lee la sonda un instante después de cerrada la ventana.
* Al ejecutar desde GRC se generan `.py` en `grc_estandar/`, `grc_hackrf/` y `hackrf_simulada/`, y archivos
  `mensajes_recibidos*.txt`, `paquetes_recibidos.bin`, `datos_recibidos.bin` y `recibido_*`; están en `.gitignore`.
* Problemas con el HackRF (no lo encuentra, dos placas en la misma PC, saturación, desvío grande): ver la tabla de la
  sección 10 de `LABORATORIO_HACKRF.md`.
* Si se modifica la trama o el canal en los `.grc`, revisar que `run_ber_sweep.py` siga usando los mismos valores de
  `ranura`, `guarda` y `sps` (constantes al comienzo del script).
