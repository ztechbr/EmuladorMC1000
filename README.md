# CCE MC-1000 em Python 3 + Flask

Emulador acadêmico do CCE MC-1000 que executa diretamente a ROM original fornecida. O BASIC, tokens, mensagens de erro, rotinas de fita e chamadas de máquina continuam sendo executados pelo firmware Z80, em vez de serem imitados por um interpretador BASIC moderno.

## Resultado de validação da ROM fornecida

- Tamanho: 16.384 bytes.
- SHA-256: `460e92dc45a8a877a4f44da9955dbe8a52d094c2aaaa2037f842c6b3af7f306a`.
- Boot real observado: `MC-1000 CCE COLOR COMPUTER`, `14618 BYTES`, `OK`.
- Entrada pela matriz física virtual validada com `PRINT 2+2`, retornando `4`.
- `GR` validado em CG2 128x64, 4 cores, controle VDG `89h`.
- `HGR` validado em RG6 256x192, controle VDG `9Fh`.
- `TEXT` retorna ao modo alfanumérico, controle VDG `01h`.

## Executar com Docker

```bash
docker compose up --build
```

Abra `http://localhost:8080`.

## Executar localmente

```bash
python -m venv .venv
. .venv/bin/activate
# Windows: .venv\\Scripts\\activate
pip install -r requirements.txt
python run.py
```

Porta padrão: `8080`. Altere com a variável de ambiente `PORT`.

## Compatibilidade implementada

- ROM original em `C000-FFFF`, com espelho de boot em `0000-1FFF` até o primeiro fetch na ROM alta.
- Z80 e interrupção NE555 de 367 Hz.
- RAM base 16 KiB e suporte estrutural à configuração de 48 KiB.
- MC6847/COL32 e 6 KiB de VRAM.
- Texto 32x16 com atributo de vídeo inverso.
- Oito modos gráficos MC6847, incluindo os modos usados por `GR` e `HGR`.
- AY-3-8910, registradores, teclado e cassette I/O.
- Teclado matricial original e modificadores SHIFT/CTRL.
- Cassete WAV PCM para `LOAD` e gravação WAV das transições produzidas por `SAVE`.
- Portas Centronics 04h/05h com captura de bytes de impressão.
- Banco da interface opcional de 80 colunas na porta 12h. Como o hardware MC6845 não acompanha a ROM fornecida, a interface 80-colunas não é inventada.
- Síntese de tons AY no navegador a partir dos registradores da máquina.

## Uso da fita

Para carregar uma gravação antiga, selecione um WAV PCM de 8 ou 16 bits em `LOAD WAV` e execute o comando `LOAD` da própria ROM. A máquina fornece ao firmware a polaridade do áudio no bit de entrada do cassette.

Para salvar, clique `REC WAV`, execute `SAVE` no BASIC e clique `STOP/SAVE WAV`. O arquivo resultante é criado a partir das mudanças de nível feitas pela ROM no pino de saída de cassette.

## Testes

Os testes não substituem o firmware. Eles iniciam a ROM e injetam teclas pela matriz da máquina:

```bash
python -m pytest -q
```

## Fidelidade

A compatibilidade de software é obtida executando a ROM original. O núcleo Z80 vendorizado é baseado no projeto `z80-python` e o hardware é modelado em Python. A emulação é orientada a instruções, não a transições elétricas de cada T-state. O vídeo digital reproduz o empacotamento de pixels e modos do MC6847, mas cores de CRT, artifact colors NTSC e características analógicas dependem do monitor e não podem ser bit-exatas em RGB de navegador. A síntese de áudio da UI é uma aproximação do AY; os registradores e acessos usados pelo firmware são preservados.

Consulte `docs/ARCHITECTURE.md` e `THIRD_PARTY_NOTICES.md`.

## Documentação interna

- `docs/ARCHITECTURE.md`: mapa de hardware e decisões de fidelidade.
- `docs/BASIC_COMPATIBILITY.md`: inventário funcional do BASIC e casos de regressão.
- `docs/REFERENCES.md`: manuais e fontes técnicas utilizadas.
- `roms/README.md`: identidade da ROM executada.
