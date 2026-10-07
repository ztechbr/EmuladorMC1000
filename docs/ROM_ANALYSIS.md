# Análise da ROM fornecida

## Arquivo de origem

Arquivo enviado: `cce_mc1000_0.zip`

SHA-256 do ZIP:

`5e5b80f78e949afc1a74412c82cc1041db85d295b042319d4a085b6af8f64abb`

Conteúdo:

```text
mc1000.rom   16384 bytes
mc1000.zip   arquivo com os dois chips para MAME
conteudo.txt descrição curta
```

Dentro de `mc1000.zip`:

```text
mc1000.ic17  8192 bytes
mc1000.ic12  8192 bytes
```

SHA-256:

```text
mc1000.ic17  cecae89529e8f5c0524ac40a5da30f30c5ebef14dbc1544d79573e337e3dab0f
mc1000.ic12  15fa09d83bba10879a9d8cdb77ae0a00bdf347149d075090077e2b8c8ea06a81
mc1000.rom   460e92dc45a8a877a4f44da9955dbe8a52d094c2aaaa2037f842c6b3af7f306a
```

Foi verificado byte a byte:

```text
mc1000.ic17 || mc1000.ic12 == mc1000.rom
```

## Identificação funcional

A imagem de 16 KiB contém o firmware/BASIC completo. Entre as strings e tokens encontrados estão o banner `MC-1000 CCE COLOR COMPUTER`, mensagens de cassete e palavras reservadas como `LOAD`, `SAVE`, `SOUND`, `COLOR`, `PLOT`, `DRAW`, `TEMPO`, `WIDTH`, `INVERSE`, `NORMAL` e `DEBUG`.

## Execução observada

A imagem foi carregada em `C000-FFFF`, com o espelho de boot previsto pelo hardware. Sem substituir o BASIC por código Python, a CPU chegou ao prompt:

```text
MC-1000 CCE COLOR COMPUTER
14618 BYTES

OK
```

Depois, a entrada foi feita pela matriz de teclado virtual, não por injeção direta de comandos no interpretador:

```basic
PRINT 2+2
```

Saída observada:

```text
 4
OK
```

Outros testes observados na ROM:

```text
GR        -> VDG 89h -> CG2 128x64
HGR       -> VDG 9Fh -> RG6 256x192
TEXT      -> VDG 01h -> alfanumérico
COLUMN 80 -> ?TI ERRO sem placa 80 colunas
COLUMN 31 -> ?PI ERRO
POKE/PEEK -> escrita/leitura real da RAM
TEMPO/SOUND -> alterações reais nos registradores AY-3-8910
```

## Por que o recode não substitui o BASIC por funções Python

Portar `PRINT`, `GOTO`, `PLOT`, `SAVE`, `DEBUG` e dezenas de rotinas uma a uma criaria uma segunda implementação com divergências inevitáveis. Para preservar comportamento, bugs e programas existentes, a ROM continua sendo a fonte de verdade. O recode em Python implementa a máquina que a ROM espera encontrar: CPU, memória, banking, vídeo, som, teclado, interrupções, fita e impressora.
