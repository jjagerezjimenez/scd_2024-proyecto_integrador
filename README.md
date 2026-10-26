# Enlace half-duplex 4-QAM en GNU Radio

Simulación de un sistema de comunicaciones digital punto a punto hecha en GNU Radio. Dos nodos (A y B) comparten un mismo canal y se turnan para transmitir. Cada uno envía un mensaje de texto en tramas con preámbulo, longitud y CRC-32, modulado en 4-QAM. Del otro lado se recupera el mensaje y se mide la tasa de error de bit (BER), que se compara con el valor teórico.


## Características

- Comunicación half-duplex por división de tiempo (TDD): nunca transmiten los dos nodos a la vez.
- Trama simple con preámbulo de 64 bits, indicación de longitud y CRC-32.
- Modulación 4-QAM diferencial con mapeo Gray y filtro de coseno realzado raíz (RRC).
- Canal con ruido blanco gaussiano (AWGN), rotación de fase y desvío de frecuencia ajustables.
- Medición de BER en tiempo real y comparación con la curva teórica.
- Usa solo bloques estándar de GNU Radio, sin módulos externos.

## Cómo funciona

### Vista general

```
Transmisor A ──┐                                              ┌──> Receptor B
               ├──> Turnos (TDD) ──> Fase + ruido ──> Conmutador
Transmisor B ──┘                                              └──> Receptor A
```

Los dos transmisores entran a un canal compartido. El canal alterna los turnos: primero transmite A, después hay un pequeño silencio, luego transmite B y otro silencio. Al final, un conmutador envía lo que transmitió A al receptor de B, y lo que transmitió B al receptor de A. Ningún nodo se escucha a sí mismo.

### Transmisor

Cada nodo toma su mensaje y arma una trama con este formato:

| Preámbulo | Longitud | Longitud (copia) | Mensaje  | CRC-32  |
|-----------|----------|------------------|----------|---------|
| 64 bits   | 16 bits  | 16 bits          | 93 bytes | 32 bits |

- El **preámbulo** es un patrón fijo que el receptor busca para saber dónde empieza cada trama.
- La **longitud** indica cuántos bytes vienen después. Va repetida para poder verificar que se leyó bien.
- El **CRC-32** permite detectar si algún bit del mensaje llegó cambiado.

Después la trama se modula en 4-QAM: los bits se agrupan de a dos y cada par define un giro de fase de la señal (0°, 90°, 180° o 270°). Es una modulación diferencial: la información está en el cambio de fase entre un símbolo y el siguiente, no en la fase absoluta. Por último, un filtro RRC suaviza la señal para limitar el ancho de banda que ocupa.

### Canal

Sobre la señal se aplican tres efectos que se pueden ajustar desde la interfaz:

- **Ruido AWGN**, calculado a partir de la relación Eb/N0 elegida.
- **Rotación de fase** fija.
- **Desvío de frecuencia** entre los osciladores de A y B. Cada receptor lo ve con signo opuesto.

### Receptor

```
Filtro adaptado -> Sincronismo de símbolo -> Lazo de Costas -> Decisión -> Decodificación diferencial -> Trama y CRC
```

1. El **filtro adaptado** (RRC) reduce el ruido y deja los símbolos bien separados entre sí.
2. El **sincronismo de símbolo** elige el mejor instante para tomar cada muestra.
3. El **lazo de Costas** corrige la fase y el desvío de frecuencia.
4. El **decisor** elige el punto de la constelación más cercano a cada muestra.
5. La **decodificación diferencial** recupera los bits. Como la información está en los cambios de fase, el resultado no depende de si el lazo de Costas quedó enganchado con la constelación girada.
6. Por último se busca el preámbulo, se lee la longitud y se verifica el CRC. Las tramas con errores se descartan.

### Medición del BER

El receptor conoce el mensaje que se envió, así que genera una copia local de la trama y la compara bit a bit con lo recibido. Cada diferencia es un bit erróneo. El BER se muestra de dos formas:

- Un gráfico con el BER de los últimos 1.000.000 de bits junto a la curva teórica.
- Valores acumulados de BER para cada nodo, y el cociente entre el BER medido y el teórico. Si el cociente se acerca a 1, la medición coincide con la teoría.

## BER teórico

Para 4-QAM coherente con mapeo Gray, la probabilidad de error de bit es:

```
p = Q( √(2·Eb/N0) )
```

Con codificación diferencial, un error en un símbolo afecta a dos decisiones consecutivas, por lo que el BER queda aproximadamente al doble:

```
BER = 2·p·(1 − p)
```

| Eb/N0 [dB] | BER teórico |
|-----------:|------------:|
| 0          | 1,5 × 10⁻¹  |
| 2          | 7,2 × 10⁻²  |
| 4          | 2,5 × 10⁻²  |
| 6          | 4,8 × 10⁻³  |
| 8          | 3,8 × 10⁻⁴  |
| 10         | 7,7 × 10⁻⁶  |


### Controles

| Control                          | Qué hace                                              |
|----------------------------------|-------------------------------------------------------|
| Eb/N0 [dB]                       | Nivel de ruido del canal. Más alto significa menos ruido. |
| Fase del canal [°]               | Rotación de fase que aplica el canal.                 |
| Desvío entre osciladores A-B [Hz]| Diferencia de frecuencia entre los dos nodos.         |
| BW lazo de Costas                | Velocidad de respuesta del lazo de Costas.            |
| BW sinc. de símbolo              | Velocidad de respuesta del sincronismo de símbolo.    |

### Pestañas

1. **Canal compartido (TDD):** turnos de cada nodo, espectro, señales transmitidas y constelación con ruido.
2. **Nodo A recibe:** diagrama de ojo, constelación antes y después del lazo de Costas, seguimiento de frecuencia, bits recibidos y BER.
3. **Nodo B recibe:** lo mismo que la pestaña anterior, para el otro nodo.

### Archivos de salida

Durante la ejecución se crean `mensajes_recibidos_A.txt` y `mensajes_recibidos_B.txt` en la carpeta desde donde se ejecuta el flowgraph. Contienen el texto de las tramas que pasaron la verificación del CRC (se guarda una de cada cien para que el archivo no crezca demasiado). Se sobrescriben en cada ejecución.

## Pruebas hechas

- **Variar Eb/N0** entre 0 y 10 dB y anotar el BER acumulado de cada nodo. Los valores medidos deberían seguir la tabla teórica. Con Eb/N0 alto hay muy pocos errores, así que conviene esperar más tiempo antes de anotar el valor.
- **Cambiar la fase del canal.** El BER no debería cambiar, porque el lazo de Costas y la codificación diferencial compensan la rotación.
- **Agregar desvío de frecuencia.** En el gráfico de frecuencia se ve cómo el lazo de Costas sigue el desvío. Si el desvío es muy grande o el ancho de banda del lazo es muy chico, el lazo puede perder el enganche y el BER sube.

## Parámetros principales

| Variable     | Valor        | Descripción                                    |
|--------------|--------------|------------------------------------------------|
| `samp_rate`  | 500 kHz      | Frecuencia de muestreo                         |
| `sps`        | 4            | Muestras por símbolo (125 kbaudios)            |
| `excess_bw`  | 0,35         | Factor de roll-off del filtro RRC              |
| `ranura`     | 2048         | Muestras de cada turno de transmisión          |
| `guarda`     | 256          | Muestras de silencio entre turnos              |
| `umbral`     | 12           | Bits erróneos tolerados al buscar el preámbulo |
| `mensaje_A`, `mensaje_B` | texto | Mensaje que envía cada nodo           |


