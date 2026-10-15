*[Read in English](README.md) · Português*

# Guia não oficial da Festa do Livro da USP

**Abra: https://jvlcapi.github.io/guia-nao-oficial-festa-do-livro/**

[![Visitantes únicos do guia](https://img.shields.io/badge/dynamic/json?url=https%3A%2F%2Fabacus.jasoncameron.dev%2Fget%2Fguia-nao-oficial-festa-do-livro%2Fvisitantes&query=%24.value&label=visitantes%20%C3%BAnicos&color=2a4fd1&cacheSeconds=3600)](https://jvlcapi.github.io/guia-nao-oficial-festa-do-livro/)

Busque nos preços de feira de todas as editoras da [Festa do Livro da USP](https://festadolivro.edusp.com.br) e monte sua lista de compras antes de ir: total na feira, quanto você economiza sobre o preço de capa, gasto por editora e por gênero, orçamento e lista para compartilhar.

Feito por leitores, de graça e de código aberto. **Não é um site oficial da Edusp nem da USP**; os preços vêm das tabelas que as editoras publicam no site oficial e podem mudar até a Festa. Confira no estande.

## Para quem vai à Festa

Não precisa de conta, cadastro nem instalar nada. É só abrir o link acima no celular ou no computador.

1. **Busque livros** na aba *Catálogo da feira*: por título, autor, editora ou assunto. Dá para filtrar por editora (estande) e por faixa de preço, e ordenar por menor preço ou maior desconto.
2. **Toque em Adicionar** nos livros que você quer.
3. **Veja a conta** na aba *Minha lista*: total na feira, economia sobre o preço de capa, gasto por editora e por gênero. Se quiser, defina um orçamento e acompanhe quanto ainda sobra.
4. **Leve para a feira.** Abra o site uma vez com internet: depois disso ele funciona mesmo sem sinal, dentro da tenda. No celular, use *Adicionar à tela inicial* para abrir como um aplicativo.

### Onde fica a minha lista

A lista fica salva **só no navegador do seu aparelho**. Nada da lista é enviado para servidor nenhum e ninguém mais vê. A única coisa que o site manda para fora é um +1, uma vez por navegador, para o contador público de visitantes que aparece no topo desta página, sem cookies. Se você limpar os dados do navegador ou usar janela anônima, a lista se perde.

### Compartilhar a lista

Em *Minha lista*, toque em **Compartilhar lista**, escreva seu nome (opcional) e toque em **Copiar link** ou **Enviar…**. Mande o link para quem quiser, por exemplo no WhatsApp.

Quem abrir o link vê a sua lista com o total e os preços atuais, e pode tocar em **Adicionar estes livros à minha lista** para copiar os livros para a própria lista. O mesmo link serve para **passar a lista do celular para o computador** (ou o contrário).

Os livros que vieram de uma lista compartilhada ganham uma **etiqueta colorida com o nome da lista** (por exemplo, "Lista de Ana"), com uma cor para cada lista importada. Acima dos livros, os filtros *Todos*, *Adicionados por mim* e uma etiqueta por lista mostram só os livros de cada origem, o que ajuda quando a lista fica grande.

O link leva só os livros escolhidos e o nome que você digitou; ele não dá acesso a mais nada do seu aparelho.

### Quando sai a edição de um ano novo

O site passa a mostrar o catálogo da nova edição e a sua lista recomeça vazia. As listas de anos anteriores continuam guardadas no aparelho e aparecem num seletor de edição, só para consulta.

---

## Para quem mantém o projeto

### Como funciona

```
site oficial da Festa (API pública + PDFs de preço das editoras)
        │  python -m festa_do_livro build        (GitHub Actions, ou local)
        ▼
data/<edição>/catalogo.json   livros, preços e editoras
data/<edição>/edicao.json     nome e datas da edição
data/<edição>/relatorio.md    conferência dos preços contra os PDFs
        │  python -m festa_do_livro assemble-site → _site/
        ▼
GitHub Pages: site/index.html + catalogo.json + edicao.json
        │
        ▼
navegador de cada pessoa: busca, lista e totais (lista salva no próprio aparelho)
```

- **Edição**: `settings.json` tem `"edition": "auto"`, que usa a edição declarada na página inicial do site oficial. Para fixar uma edição, troque por exemplo para `"28-festa-do-livro-da-usp"` ou passe a variável `FESTA_EDITION`.
- **Leitura dos PDFs**: cada lista é lida de dois jeitos (células da tabela e posição do texto) e fica o resultado mais completo. Nomes cortados pela célula são completados pelo texto do PDF.
- **Conferência**: cada preço de capa e de feira precisa aparecer na linha do mesmo ISBN no PDF. O que não bate vai para o relatório.
- **Site**: estático, sem servidor nem conta. A lista fica no `localStorage`, separada por edição, e os preços dela são atualizados quando o catálogo muda. O link de compartilhamento leva a edição, o nome e os identificadores dos livros no fragmento da URL (`#lista=...`), que o navegador não envia ao servidor. O `site/sw.js` guarda o site e o catálogo no aparelho (rede primeiro, cache como reserva) para funcionar sem internet.
- **Contador de visitantes**: na primeira vez que um navegador abre o site publicado (`jvlcapi.github.io`), a página chama `abacus.jasoncameron.dev/hit/...` e anota no `localStorage` que já contou. Cópias locais e forks não contam. O selo do topo lê o total com `/get/...`, sem somar. Não é exato (quem limpa o navegador conta de novo, e quem só usa o site sem internet não conta), mas dá a dimensão do alcance.

### Atualização automática (GitHub Actions)

- **Atualizar catálogo** (`atualizar-catalogo.yml`): roda pelo botão *Run workflow* (com a edição opcional) e todo dia às 6h de Brasília, de setembro a dezembro. Roda os testes, gera catálogo e relatório, mostra o relatório no resumo da execução e, se algo mudou, faz commit e publica o site.
- **Publicar site** (`publicar-site.yml`): monta `_site/` com a edição atual (`data/edicao-atual.json`) e publica no GitHub Pages. Também roda quando `site/` ou os dados mudam por push.
- **Testes** (`testes.yml`): em todo push e pull request.
- **Guardar contador de visitantes** (`guardar-contador-de-visitantes.yml`): toda segunda às 7h de Brasília, anota o total em `data/visitantes.csv` quando ele mudou. Assim o histórico fica no repositório mesmo que o serviço do contador suma, e a leitura semanal impede que o contador expire (o serviço apaga contadores sem acesso por 6 meses).

### Roteiro do dia em que a lista sair

1. Confirme a edição: `python -m festa_do_livro detect-edition` (ou veja a página de editoras no site oficial).
2. Rode o workflow **Atualizar catálogo** (vazio = `auto`, ou informe a edição).
3. Abra o resumo da execução e leia o relatório: total de livros, listas não lidas e divergências por editora. Editora com formato novo aparece com 0 livros ou com muitas divergências.
4. Se precisar ajustar o leitor, corrija, adicione um teste com o PDF da editora em `tests/fixtures/price_lists/` e rode de novo.
5. Abra o site e confira que o número e as datas da nova edição aparecem no topo.

### Rodar localmente

```bash
python3 -m venv .venv
.venv/bin/pip install -e '.[test]'
.venv/bin/pytest -q
.venv/bin/python -m festa_do_livro detect-edition
.venv/bin/python -m festa_do_livro build
.venv/bin/python -m festa_do_livro assemble-site
python3 -m http.server 8765 --bind 127.0.0.1 --directory _site
```

O `build` baixa os PDFs para `cache/<edição>/` (fora do Git) e escreve em `data/`. Para outra edição: `--edition 28-festa-do-livro-da-usp`. Depois do último comando, o site fica em http://127.0.0.1:8765.

### Segredos

Nenhuma chave é necessária: o site oficial e a API são públicos, o commit automático usa o `GITHUB_TOKEN` que o GitHub gera em cada execução e a publicação no Pages usa o token temporário do próprio GitHub (OIDC). O repositório tem *secret scanning* e *push protection* ligados. Se um dia for preciso uma chave (por exemplo, para notificações):

1. Cadastre em *Settings → Secrets and variables → Actions*.
2. Passe para o passo do workflow como `env: NOME: ${{ secrets.NOME }}` e leia com `os.environ` no código.
3. Para uso local, coloque num `.env` (já ignorado pelo Git), nunca em `settings.json`.

O teste `tests/test_repository_hygiene.py` falha se algum arquivo versionado tiver padrão de token ou chave, e confere que `.env` e `cache/` estão ignorados. O catálogo também descarta links com parâmetros de credencial que vêm em algumas listas de editoras.

### Estrutura

```
settings.json                 edição ("auto" ou identificador) e endereço do site oficial
src/festa_do_livro/
  fair_site.py                página inicial, API do evento e das editoras
  price_list_download.py      download dos PDFs com cache
  pdf_reading.py              extração de tabelas, texto e posições
  table_parser.py             leitor por células da tabela
  position_parser.py          leitor por posição do texto
  catalog_builder.py          limpeza, nomes completos, links seguros, catalogo.json
  price_verification.py       conferência de preços e relatório
  site_assembly.py            monta a pasta publicada no GitHub Pages
site/                         site público (página, cache offline, ícone, manifesto)
data/                         catálogos gerados (um diretório por edição) e visitantes.csv com o total semanal de visitantes
```

## Licença

Código, site e documentação: [PolyForm Noncommercial 1.0.0](LICENSE.md). Você pode usar, estudar, modificar e compartilhar para fins não comerciais, desde que toda cópia mantenha os termos da licença e a linha de crédito:

```
Required Notice: Copyright 2026 João Vitor Lopes Capi (https://github.com/jvlcapi)
```

Uso comercial só com autorização por escrito do autor.

Os dados dos livros (títulos, autores e preços) vêm das listas que as editoras publicam no site oficial da Festa e não estão cobertos por esta licença. Os PDFs em `tests/fixtures/price_lists/` são essas listas públicas, guardadas só para testar o leitor.
