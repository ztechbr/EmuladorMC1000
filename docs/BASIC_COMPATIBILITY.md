# Compatibilidade do BASIC da ROM

Este projeto não contém implementações Python separadas para os comandos abaixo. Eles são listados para facilitar os testes, mas quem interpreta e executa a sintaxe é a ROM original do MC-1000.

## Edição e programa

`REM`, `NEW`, `AUTO`, `LIST`, `EDIT`, `DIM`, `LET` opcional.

## Operadores e funções numéricas

Operadores aritméticos `+`, `-`, `*`, `/`, exponenciação, relacionais, `AND`, `OR`, `NOT`.

Funções: `ABS`, `SGN`, `INT`, `SQR`, `SIN`, `COS`, `TAN`, `ATN`, `EXP`, `LOG`, `RND`, `DEF FN` e `FN`.

## Strings

`LEN`, `LEFT$`, `MID$`, `RIGHT$`, `STR$`, `VAL`, `CHR$`, `ASC`.

## Controle de fluxo

`RUN`, `STOP`, `CONT`, `END`, `GOTO`, `ON ... GOTO`, `IF ... THEN`, `IF ... GOTO`, `FOR`, `TO`, `STEP`, `NEXT`, `GOSUB`, `RETURN`, `ON ... GOSUB`.

## Entrada, saída e dados

`INPUT`, `READ`, `DATA`, `RESTORE`, `PR#`, `PRINT`, `SPC`, `TAB`, `VTAB`.

## Texto e tela

`TEXT`, `HOME`, `NORMAL`, `INVERSE`, `WIDTH`, `POS`, `COLUMN`.

No hardware base reproduzido aqui, `COLUMN 80` retorna `?TI ERRO`, como a própria ROM faz quando a placa opcional de 80 colunas não está instalada. `COLUMN 32` retorna ao VDG normal. Valores diferentes de 32/80 produzem `?PI ERRO` pela ROM.

## I/O e linguagem de máquina

`INP`, `OUT`, `WAIT`, `PEEK`, `POKE`, `CALL`, `USR`, `FRE`, `DEBUG`.

Como a CPU Z80 e o mapa de memória são executados de fato, `PEEK/POKE`, `CALL`, `USR` e o monitor `DEBUG` não são simulados por strings no servidor.

## Cassete

`SAVE`, `LOAD`, `SAVE * matriz`, `LOAD * matriz`, `TLOAD`.

O arquivo WAV é apresentado à entrada de cassette do hardware virtual. A interpretação do nome, cabeçalho, dados e checksum é feita pelas rotinas da ROM.

## Gráficos

`GR`, `COLOR`, `HGR`, `PLOT`, `DRAW`, `UNPLOT`, `UNDRAW`, `SET`.

A ROM fornecida foi executada para verificar:

- `GR` -> controle VDG `89h`, MC6847 CG2, 128x64, 4 cores.
- `HGR` -> controle VDG `9Fh`, MC6847 RG6, 256x192.
- `TEXT` -> controle VDG `01h`.

O frontend também interpreta CG1, RG1, CG2, RG2, CG3, RG3, CG6, RG6, SG4 e SG6 quando software em linguagem de máquina altera diretamente a porta de vídeo.

## Som

`TEMPO`, `SOUND`.

Os acessos reais da ROM aos registradores AY-3-8910 chegam ao modelo Python. A UI usa esses registradores para síntese WebAudio. O protocolo do firmware é preservado, enquanto a etapa analógica de áudio é aproximada no navegador.

## Utilitários e depuração

`CLEAR`, `TRO N`, `TRO F`, `DEBUG`, `SLOW`, `FAST`, `EXIT`.

Algumas instruções possuem bugs ou limitações do firmware original. Como o projeto executa a ROM, essas peculiaridades não são corrigidas silenciosamente.

## Casos de regressão incluídos

Os testes automatizados validam pelo menos:

```basic
PRINT 2+2
POKE 4096,42:PRINT PEEK(4096)
GR
HGR
TEXT
COLUMN 80
COLUMN 31
COLUMN 32
```

A ampliação natural da suíte é adicionar programas de regressão para cada comando sem mudar o princípio de arquitetura: o teste deve dirigir o teclado/portas e observar a máquina, não chamar uma função Python chamada `PRINT`, `PLOT`, `SOUND`, etc.
