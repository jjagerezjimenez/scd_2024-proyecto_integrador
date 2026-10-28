# HackRF simulada: ensayo del laboratorio en una sola PC

Esta carpeta sirve para ensayar **todo el procedimiento del laboratorio sin las placas**:

1. Un programa de Python (`emulador_hackrf.py`) hace de "dos HackRF One + el aire entre ellas". Se deja
   corriendo en un *radioconda Prompt*.
2. En GNU Radio Companion se abren las versiones simuladas del transmisor y del receptor. Son copias exactas de
   los `.grc` del laboratorio, salvo el bloque de la placa.
3. Al final se reconstruye el archivo recibido con `reconstruir_archivo.py`, igual que en el laboratorio.

Los `.grc` del laboratorio (`grc_hackrf/`) **no se tocan**: el día del laboratorio se usan tal cual.

## Qué hay en la carpeta

| Archivo | Para qué |
|---|---|
| `emulador_hackrf.py` | El emulador: se deja corriendo en un *radioconda Prompt* (Ctrl+C para cortarlo) |
| `hackrf_tx_archivo_sim.grc` | Transmisor: igual a `grc_hackrf/hackrf_tx_archivo.grc`, pero manda las muestras al emulador |
| `hackrf_rx_archivo_sim.grc` | Receptor: igual a `grc_hackrf/hackrf_rx_archivo.grc`, pero recibe las muestras del emulador |
| `generar_grc_simulados.py` | Arma los dos `.grc` simulados a partir de los de `grc_hackrf/` (no se editan a mano) |
| `prueba_completa.py` | Prueba automática de punta a punta: 9 casos en ~40 s, sin ventanas |
| `capturas/` | Cómo se ven las interfaces con el emulador (valores por defecto) |

## Cómo funciona

```
  hackrf_tx_archivo_sim.grc            emulador_hackrf.py              hackrf_rx_archivo_sim.grc
                              +------------------------------------+
                              | HackRF TX  ->  aire  ->  HackRF RX |
  ... Multiply Const --TCP--> | DAC 8 bits   atenuación  ruido     | --UDP--> Socket PDU
                              | potencia     cristales   ganancias |          -> PDU to Tagged Stream
                              | fuga del LO  sintonía    ADC 8 bits|          -> IChar To Complex
  frecuencia y ganancias ---> |      2 millones de muestras/s      | <---     -> Tag Gate -> ... (igual)
                              +------------------------------------+     frecuencia y ganancias
```

En el `.grc` real, el bloque **Soapy HackRF** manda las muestras a la placa por USB y le pide una frecuencia y
unas ganancias. En el simulado, ese bloque se reemplazó por bloques de red **estándar** de GNU Radio que hacen lo
mismo con el emulador, todo dentro de la PC (dirección `127.0.0.1`):

| En el laboratorio | En la versión simulada |
|---|---|
| TX: `Soapy HackRF Sink` | `TCP Sink`: si el emulador no lee, el TX espera, igual que con la placa |
| RX: `Soapy HackRF Source` | `Socket PDU` (UDP) → `PDU to Tagged Stream` → `IChar To Complex` → `Tag Gate` |
| Frecuencia y ganancias de cada placa | Variable `ajustes_hackrf` + `Message Strobe` + `Socket PDU`: avisan los valores 5 veces por segundo |

El emulador le manda al RX pares de bytes (I, Q) de 8 bits, que es lo mismo que manda una HackRF por USB.
`IChar To Complex` los pasa a números complejos entre −1 y 1, igual que el driver. `Tag Gate` borra las marcas que
`PDU to Tagged Stream` pone en cada paquete de red. Todo lo demás (filtros, AGC, FLL, sincronismo, Costas, CRC,
archivos) es **exactamente** lo del laboratorio.

## Paso a paso

1. Abrir un **radioconda Prompt**, ir a la carpeta del proyecto y arrancar el emulador:

        cd ...\proyecto_sdr_4qam_halfduplex
        python hackrf_simulada\emulador_hackrf.py

    Dejar esa ventana abierta. **No hacer clic adentro**: Windows pausa el programa mientras hay texto
    seleccionado. Si pasa, apretar Esc.

2. En GNU Radio Companion, abrir `hackrf_simulada/hackrf_rx_archivo_sim.grc` y apretar **F6**.
    Primero el receptor, como en el laboratorio, para que el AGC se acomode al ruido.

3. Abrir `hackrf_simulada/hackrf_tx_archivo_sim.grc` y apretar **F6**. Por defecto manda
    `grc_hackrf/archivo_a_enviar.txt` 3 veces. Para mandar otro archivo, cambiar el bloque *Parameter*
    `archivo` (ruta completa, o relativa a la carpeta `hackrf_simulada/`).

4. Mirar las dos ventanas y el emulador, que cada 2 s muestra lo que pasa en el "aire" (ver abajo).

5. Cuando "Pasadas enviadas" llega al número de repeticiones, esperar un segundo y cerrar las dos ventanas.
    Después, en el prompt:

        python reconstruir_archivo.py hackrf_simulada\paquetes_recibidos.bin

    Escribe `hackrf_simulada\recibido_archivo_a_enviar.txt` y dice si la huella SHA-256 coincide con la original.

El emulador puede quedar corriendo todo el tiempo: se pueden abrir y cerrar el TX y el RX las veces que haga falta.

### Qué muestra el emulador

```
Emulador de dos HackRF One listo (Ctrl+C para cortar)
  aire: 45 dB de atenuación | cristales: TX +9.0 ppm, RX -5.0 ppm (desvío +12.8 kHz a 915 MHz)
[    4 s] TX: apagado
          RX: 914.600 MHz (LNA 16 dB, VGA 20 dB, amplificador no), nivel -40.8 dBFS
  >> se conectó el TX
[    6 s] TX: transmite en 914.600 MHz, -37.0 dBm (VGA 20 dB, amplificador no)
          RX: 914.600 MHz (LNA 16 dB, VGA 20 dB, amplificador no), nivel -35.8 dBFS
              señal en el RX: -82.0 dBm (-36.0 dBFS), S/R 11.4 dB en 2 MHz, Es/N0 ~ 20.4 dB, desvío +12.8 kHz
```

* **914.600 MHz**: cada placa se sintoniza 400 kHz por debajo de la frecuencia elegida (915 MHz). La señal va
  corrida +400 kHz para que no la toque el pico del oscilador, que queda en el centro.
* **−37 dBm**: potencia que sale del TX. **−82 dBm**: la que llega a la antena del RX, después de 45 dB de aire.
* **dBFS**: nivel respecto del máximo del ADC de 8 bits (0 dBFS = escala completa). "nivel" es todo lo que entra
  (ruido + señal); en la línea de la señal, solo la señal.
* **S/R en 2 MHz**: señal contra todo lo demás (ruido térmico + error del ADC de 8 bits), en el ancho de banda
  muestreado. **Es/N0 ≈ S/R + 9 dB**, porque la señal usa 250 k símbolos/s de los 2 M muestras/s. Debería coincidir con
  lo que estima el RX: allí se muestra **Eb/N0 = Es/N0 − 3 dB**.
* **desvío**: diferencia de frecuencia entre los osciladores de las dos placas. Es lo que tiene que medir el
  indicador "Desvío de frecuencia" del RX.
* Avisos: `SATURA` (el ADC del RX llega a ±1), `el DAC del TX recorta`, `la señal NO llega`, `¡CUIDADO!` (con
  esa potencia una HackRF real se puede dañar) y `el emulador se atrasó` (la PC no dio abasto).

## Ejercicios para hacer antes del laboratorio

Cada fila es un caso de `prueba_completa.py`; los números son los que se obtuvieron en esta PC.

| # | Qué hacer | Qué se ve | Lo que enseña |
|---|---|---|---|
| 1 | Todo por defecto | Emulador: Es/N0 ≈ 20,4 dB, desvío +12,8 kHz. RX: Eb/N0 ≈ 17,4 dB y desvío +12,8 kHz. Archivo idéntico, 0 paquetes perdidos | El RX mide bien el desvío y la relación señal/ruido |
| 2 | Archivo de 40 kB (2 pasadas) | 402 de 402 paquetes; el último llega a los ~3 s, como dice la teoría | El sistema funciona en tiempo real, a 2 M muestras/s |
| 3 | Subir la **VGA del RX** a 36 dB | La señal pasa de −36 a −20 dBFS y el Es/N0 de 20,4 a 23,9 dB | Con poca ganancia la señal ocupa pocos niveles del ADC de 8 bits: conviene que quede entre −30 y −10 dBFS |
| 4 | Emulador con `--atenuacion 53` (antenas más lejos) | Es/N0 ≈ 12,5 dB; se pierde ~2–4 % de los paquetes (teoría ~2,5 %); con 5 pasadas el archivo llega idéntico | Por qué se manda el archivo varias veces |
| 5 | Frecuencia del RX en **917** MHz | `la señal NO llega`; 0 paquetes | TX y RX tienen que estar en la misma frecuencia |
| 6 | LNA 40, VGA 50 y amplificador del RX | `SATURA 65 %`; la señal cruda toca ±1 | Demasiada ganancia satura el ADC: bajar primero la VGA |
| 7 | **Amplitud digital 0,7** en el TX | `el DAC del TX recorta`: los picos de I y Q pasan de ±1 | No subir la amplitud digital por encima de ~0,6 |
| 8 | Frecuencia del RX en 915,025 MHz | Desvío −12,2 kHz (+12,8 − 25); el FLL lo corrige y el archivo llega idéntico | El FLL corrige errores de sintonía de decenas de kHz |
| 9 | Emulador con `--atenuacion 0`, TX con VGA 47 y amplificador | `¡CUIDADO!`: llegan +4 dBm al RX; no se recibe nada | Por qué **nunca** se unen TX y RX con cable sin atenuador |

Para los ejercicios 4 y 9, cortar el emulador con Ctrl+C y volver a arrancarlo con la opción; por ejemplo
`python hackrf_simulada\emulador_hackrf.py --atenuacion 53`. Los demás se hacen moviendo los controles de las
ventanas mientras todo corre.

## Qué imita el emulador (y qué no)

| Efecto de las placas reales | Cómo lo imita | Por defecto | Opción |
|---|---|---|---|
| DAC del TX de 8 bits | Redondea a 8 bits y recorta fuera de ±1 | — | — |
| Fuga del oscilador local del TX | Suma una constante (pico en el centro del espectro) | 0,02 | — |
| Potencia del TX | +10 dBm a escala completa con VGA 47 dB y amplificador; −1 dB por cada dB menos de VGA; −14 dB sin amplificador | −37 dBm (VGA 20, amplitud 0,5) | controles del TX |
| Aire (o cable con atenuador) | Atenuación y una fase cualquiera | 45 dB (antenas a unos metros) | `--atenuacion` |
| Cristales distintos | Error en ppm de cada placa: corre la frecuencia **y** el ritmo de muestreo | TX +9 ppm, RX −5 ppm (+12,8 kHz) | `--ppm-tx`, `--ppm-rx` |
| Calentamiento del cristal | El del TX se corre hasta 1 ppm en unos minutos | 1 ppm | `--deriva` |
| Ruido de fase | Paso de fase aleatorio en cada muestra | 0,003 rad | — |
| Sintonía | La señal se corre la diferencia de frecuencias; más de 1 MHz, no llega | — | controles de frecuencia |
| Ruido térmico del RX | −174 dBm/Hz + figura de ruido de 14 dB (8 dB con amplificador): −97 dBm en 2 MHz | — | — |
| Ganancias del RX | LNA 0–40 dB de a 8, VGA 0–62 dB de a 2, amplificador +11 dB (como el driver) | LNA 16, VGA 20 | controles del RX |
| ADC del RX de 8 bits | −10 dBm después de las ganancias llenan el ADC; redondea y satura | — | — |
| Componente continua del RX | Pico en el centro del espectro | — | — |
| Reloj de la placa | Exactamente 2 M muestras/s en tiempo real | 2 Ms/s | `--muestreo` |

**Lo que no imita:** reflexiones y desvanecimientos (personas que se mueven), otras señales de la banda de 915 MHz,
desbalance entre I y Q (imagen espejada), la forma exacta del filtro analógico ni problemas de USB. Además, los dBm
y la figura de ruido son aproximados: del orden de los de una HackRF One a 915 MHz, no medidos.

Por eso el ensayo no reemplaza la prueba real. Lo que sí comprueba es que:

* los `.grc` y `reconstruir_archivo.py` funcionan juntos, en tiempo real y en esta PC;
* el procedimiento está claro;
* se sabe cómo reacciona el sistema a cada control.

## Prueba automática

    python hackrf_simulada\prueba_completa.py          # los 9 casos, ~40 s
    python hackrf_simulada\prueba_completa.py 4 8      # solo algunos casos

Para cada caso arranca un emulador, corre el RX y el TX simulados sin ventanas, reconstruye el archivo y revisa el
resultado: archivo idéntico, desvío medido, avisos del emulador. Antes comprueba que los `.grc` simulados estén
al día con los de `grc_hackrf/`. Lo que genera queda en `build/hackrf_simulada/`.

## Si se cambian los `.grc` del laboratorio

Los `_sim.grc` se generan, no se editan: si se modifica `grc_hackrf/hackrf_tx_archivo.grc` o
`hackrf_rx_archivo.grc`, volver a correr

    python hackrf_simulada\generar_grc_simulados.py

Si alguien se olvida, `prueba_completa.py` avisa que quedaron desactualizados.

## Problemas comunes

| Qué pasa | Causa y solución |
|---|---|
| Al apretar F6 en el TX aparece `[TCP Sink] Connection error: No se puede establecer una conexión ya que el equipo de destino denegó expresamente dicha conexión` y la ventana no abre | El emulador no está corriendo. Cortar el TX con el botón *Kill* de GRC, arrancar el emulador y volver a apretar F6 |
| La ventana del RX abre, pero no se mueve nada | El emulador no está corriendo (el RX espera muestras) |
| El emulador dice `No se pudieron abrir los puertos` | Ya hay otro emulador abierto: usar ese o cortarlo con Ctrl+C |
| El RX no arranca y GRC muestra `UnicodeDecodeError: 'utf-8' codec can't decode byte 0xf3 ...` | Ya hay otra ventana del RX simulado abierta. Es el aviso de Windows "solo se permite un uso de cada dirección", que viene en español y Python no lo puede leer |
| GRC muestra `RuntimeError: SoapySDR::Device::make() no match` | Se abrió el `.grc` del laboratorio (`grc_hackrf/`), que busca una placa real: abrir el de `hackrf_simulada/` |
| GRC avisa `This flow graph may not have flow control` | Es normal: el ritmo lo pone el emulador, que hace de reloj de la placa |
| Terminaron las pasadas: el emulador dice `el TX se desconectó` y `TX: apagado`, pero la ventana del TX sigue abierta | Es normal; cerrar la ventana. Con la placa real también hay que cerrarla |
| "Pasadas enviadas" llega al final medio segundo antes de que termine la señal | Entre el contador y la placa hay buffers (~0,5 s); con la HackRF real pasa lo mismo |
| El emulador dice `el emulador se atrasó` | La PC estuvo ocupada, o se hizo clic en la ventana del emulador (Esc) |

## Detalles técnicos (por qué estos bloques)

* **No se usaron los bloques ZMQ**, que son lo habitual para unir programas con GNU Radio, porque en esta PC la
  biblioteca ZeroMQ falla apenas crea un socket: `Bad file descriptor (epoll.cpp:73)`. Los bloques TCP/UDP de
  `gr-network` usan los sockets comunes de Windows y funcionan.
* **No se usó `UDP Source`**: cuando no encuentra datos, el planificador de GNU Radio lo hace esperar 250 ms. A 2 M
  muestras/s eso pierde medio millón de muestras cada vez. `Socket PDU` recibe en su propio hilo y no pierde
  nada: se probaron 6 millones de muestras sin pérdidas.
* **No se usó `TCP Source`**: en Windows no funciona, porque usa `os.dup` sobre el socket.
* El cambio de ritmo de muestreo entre las dos placas se hace con un interpolador sinc de 16 coeficientes y 256
  fases. Su error, −48 dB, queda muy por debajo del ruido.
