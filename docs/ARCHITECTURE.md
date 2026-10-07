# Arquitetura de compatibilidade MC-1000

## 1. Estratégia

O interpretador BASIC não é reimplementado semanticamente. A ROM original de 16 KiB é executada sobre um Z80 em Python. Isso preserva tokens, mensagens, cálculos, fluxo de comandos, PEEK/POKE, INP/OUT, rotinas de fita e peculiaridades do firmware.

Arquitetura:

```text
Browser
  | REST / keyboard / canvas / WebAudio
Flask Controllers
  |
MC1000 Machine Model
  |-- Z80 CPU
  |-- Memory banking
  |-- MC6847 control + VRAM
  |-- AY-3-8910 registers
  |    |-- keyboard matrix
  |    `-- cassette I/O
  |-- NE555 IRQ
  `-- Centronics
  |
Original 16 KiB ROM
```

## 2. Clock e interrupção

- Z80: 3.579.545 Hz.
- AY-3-8910: 3.579.545 / 2 Hz.
- NE555: 367 Hz.
- O pulso de IRQ é curto, aproximadamente 6,93 us, em vez de permanecer pendente indefinidamente.

Esse detalhe foi necessário para o boot permanecer coerente com o hardware.

## 3. Mapa de memória

| Faixa | Base 16 KiB | Expansão 48 KiB |
|---|---|---|
| 0000-1FFF | ROM no boot, depois RAM | ROM no boot, depois RAM |
| 2000-27FF | RAM / banco 80 colunas | RAM / banco 80 colunas |
| 2800-3FFF | RAM | RAM |
| 4000-7FFF | aberto | RAM |
| 8000-97FF | VRAM MC6847 ou banco | VRAM MC6847 ou RAM |
| 9800-BFFF | aberto | RAM |
| C000-FFFF | ROM | ROM |

O primeiro fetch de opcode em `C000-FFFF` remove o espelho de ROM de `0000-1FFF`, reproduzindo o efeito de banking do driver de referência.

## 4. Portas I/O

| Porta | Função |
|---|---|
| 04h | Centronics busy / strobe |
| 05h | Centronics data |
| 12h | banco de vídeo da interface 80 colunas |
| 20h | AY register address |
| 40h | AY register read |
| 60h | AY register write |
| 80h | MC6847 attributes e banking |

Bits da porta 80h:

```text
bit 0  acesso da CPU à VRAM
bit 1  CSS
bit 2  GM0
bit 3  GM1
bit 4  GM2
bit 5  INT/EXT
bit 6  A/S
bit 7  A/G
```

## 5. Vídeo MC6847

O frontend lê a VRAM real da máquina. Em texto, o bit 7 de cada byte aciona inversão e os 6 bits baixos selecionam o caractere. Em gráficos, `A/G` e `GM2..GM0` determinam um dos oito modos:

| GM | Nome | Resolução | Pixel |
|---:|---|---:|---|
| 0 | CG1 | 64x64 | 2 bits |
| 1 | RG1 | 128x64 | 1 bit |
| 2 | CG2 | 128x64 | 2 bits |
| 3 | RG2 | 128x96 | 1 bit |
| 4 | CG3 | 128x96 | 2 bits |
| 5 | RG3 | 128x192 | 1 bit |
| 6 | CG6 | 128x192 | 2 bits |
| 7 | RG6 | 256x192 | 1 bit |

A ROM fornecida foi executada para validar que `GR` seleciona CG2 e `HGR` seleciona RG6.

## 6. Teclado

A matriz possui 8 linhas, cada uma selecionada por bits ativos em nível baixo escritos pela porta A do AY. A porta B do AY lê seis colunas mais SHIFT e CTRL. O browser envia key-down e key-up, portanto combinações como SHIFT + letra passam pela mesma lógica usada no equipamento.

## 7. Cassete

A ROM continua responsável por `LOAD` e `SAVE`. O host apenas converte:

- WAV PCM -> polaridade do sinal -> bit 7 da leitura de teclado/cassete.
- bit 7 da porta A do AY -> arestas temporizadas -> WAV PCM.

Isso evita inventar um novo formato de arquivo para fita. Para gravações reais, ruído, wow/flutter e clipping do equipamento físico ainda podem exigir pré-processamento do áudio.

## 8. AY-3-8910

Os 16 registradores e máscaras de largura são preservados. A UI usa WebAudio para tornar audíveis os três geradores de tom. A síntese de UI não pretende reproduzir eletricamente filtros, resistores, envelope e ruído com precisão analógica. O estado de registradores observado pela ROM permanece no modelo da máquina.

## 9. Interface de 80 colunas

O mapa conhecido prevê MC6845 e VRAM em `2000-27FF`, com controle de banco em `12h`. O driver público de referência também mantém as portas 10h/11h comentadas, e a placa de 80 colunas não faz parte da ROM/hardware enviado. Por isso o projeto não inventa um periférico inexistente. Programas que dependam fisicamente dessa placa precisam de uma implementação separada baseada em hardware/ROM da placa.

## 10. Critério de compatibilidade

A meta é firmware-first:

1. carregar os bytes exatos da ROM;
2. reproduzir barramentos e dispositivos que a ROM observa;
3. validar por boot e programas BASIC executados pela matriz de teclado;
4. evitar atalhos que implementem comandos BASIC no Flask.

Isso é mais fiel do que portar cada comando para funções Python, pois mantém também comportamento não documentado e decisões internas da ROM.
